from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from datetime import timedelta
from .forms import LetterUploadForm, ClassificationCategoriesForm
from .models import Letter, AnalysisResult, GeneratedResponse, ClassificationCategory, LetterQuestion
from .services.llm_client import LLMClient

llm_client = LLMClient()

def classification_settings(request):
    """Настройка классификаторов"""
    custom_categories = ClassificationCategory.objects.filter(is_active=True).order_by('number')

    if request.method == 'POST':
        form = ClassificationCategoriesForm(request.POST)
        if form.is_valid():
            categories_data = form.cleaned_data['categories_json']

            # Предупреждение о потере данных
            if Letter.objects.exclude(classification__isnull=True).exists() or AnalysisResult.objects.exists():
                messages.warning(request,
                                 "Внимание! Все существующие результаты анализа писем будут удалены, "
                                 "так как изменятся категории классификации. Это необходимо для "
                                 "предотвращения конфликта данных."
                                 )
                # Сохраняем данные в сессии для подтверждения
                request.session['pending_categories'] = categories_data
                return redirect('confirm_classification_change')

            # Если нет существующих данных, сразу применяем изменения
            return apply_classification_changes(request, categories_data)
    else:
        # Инициализируем пустую форму
        form = ClassificationCategoriesForm()

    # Получаем базовые категории из модели Letter
    base_classification_choices = Letter.BASE_CLASSIFICATION_CHOICES

    context = {
        'form': form,
        'custom_categories': custom_categories,
        'base_classification_choices': base_classification_choices,  # Добавляем базовые категории
        'has_existing_data': Letter.objects.exclude(
            classification__isnull=True).exists() or AnalysisResult.objects.exists(),
    }
    return render(request, 'classification_settings.html', context)


def confirm_classification_change(request):
    """Подтверждение изменения классификаторов с удалением данных"""
    if 'pending_categories' not in request.session:
        return redirect('classification_settings')

    categories_data = request.session['pending_categories']

    if request.method == 'POST':
        if 'confirm' in request.POST:
            return apply_classification_changes(request, categories_data)
        else:
            # Отмена - очищаем сессию и возвращаем к настройкам
            del request.session['pending_categories']
            return redirect('classification_settings')

    # Подсчет данных для удаления
    letters_count = Letter.objects.exclude(classification__isnull=True).count()
    analysis_count = AnalysisResult.objects.count()
    responses_count = GeneratedResponse.objects.count()

    context = {
        'letters_count': letters_count,
        'analysis_count': analysis_count,
        'responses_count': responses_count,
        'new_categories': categories_data,  # Передаем как есть - список словарей
    }
    return render(request, 'confirm_classification_change.html', context)


def apply_classification_changes(request, categories_data):
    """Применение изменений классификаторов"""
    try:
        with transaction.atomic():
            # Деактивируем старые категории
            ClassificationCategory.objects.filter(is_active=True).update(is_active=False)

            # Создаем новые категории из JSON данных
            for category in categories_data:
                ClassificationCategory.objects.create(
                    number=category['number'],
                    name=category['name'],
                    description=category.get('description', ''),
                    is_active=True
                )

            # Удаляем все данные анализа
            AnalysisResult.objects.all().delete()
            GeneratedResponse.objects.all().delete()

            # Сбрасываем классификацию у всех писем
            Letter.objects.all().update(
                classification=None,
                summary='',
                criticality_level=None,
                response_style=None,
                processing_time_hours=None,
                sla_deadline=None,
                final_response='',
                status='new'
            )

            messages.success(request, "Классификаторы успешно обновлены! Все письма помечены для повторного анализа.")

            # Очищаем сессию
            if 'pending_categories' in request.session:
                del request.session['pending_categories']

    except Exception as e:
        messages.error(request, f"Ошибка при обновлении классификаторов: {str(e)}")

    return redirect('classification_settings')


def letter_list(request):
    """Главная страница - список всех писем"""
    # Базовый queryset
    letters = Letter.objects.all()

    # Определяем временной порог для "истекающего срока" (например, 24 часа)
    time_threshold = timezone.now() + timedelta(hours=24)

    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        letters = letters.filter(status=status_filter)

    # Фильтрация по классификации - преобразуем строку в число
    classification_filter = request.GET.get('classification')
    if classification_filter:
        try:
            classification_value = int(classification_filter)
            letters = letters.filter(classification=classification_value)
        except (ValueError, TypeError):
            # Если не удалось преобразовать в число, игнорируем фильтр
            pass

    # Аннотируем письма флагом "истекающий срок"
    from django.db.models import Case, When, Value, BooleanField
    letters = letters.annotate(
        is_urgent=Case(
            When(
                sla_deadline__isnull=False,
                sla_deadline__lte=time_threshold,
                then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    # Сортируем: сначала истекающие по сроку (по возрастанию дедлайна),
    # затем остальные по дате загрузки (по убыванию)
    letters = letters.order_by('-is_urgent', 'sla_deadline', '-uploaded_at')

    # Получаем текстовые представления для отображения
    status_choices = dict(Letter.STATUS_CHOICES)
    classification_choices = Letter.get_classification_choices()

    print("=== ОТЛАДКА letter_list ===")
    print(f"classification_choices: {classification_choices}")
    if classification_choices:
        print(f"Первый элемент: {classification_choices[0]}")
        print(f"Длина первого элемента: {len(classification_choices[0])}")
    print("===========================")

    context = {
        'letters': letters,
        'status_choices': status_choices.items(),
        'classification_choices': classification_choices,
        'now': timezone.now(),
        'time_threshold': time_threshold,
    }

    return render(request, 'letter_list.html', context)


def upload_letter(request):
    """Страница загрузки нового письма"""
    if request.method == 'POST':
        form = LetterUploadForm(request.POST)
        if form.is_valid():
            # Сохраняем письмо со статусом "новое"
            letter = form.save(commit=False)
            letter.status = 'new'
            letter.save()

            # Перенаправляем на страницу анализа
            return redirect('analyze_letter', letter_id=letter.id)
    else:
        form = LetterUploadForm()

    return render(request, 'upload_letter.html', {'form': form})


def analyze_letter(request, letter_id):
    """Анализ письма нейросетью"""
    letter = get_object_or_404(Letter, id=letter_id)

    if letter.status != 'new':
        return redirect('analysis_results', letter_id=letter.id)

    # Для LLM используем метод с полными данными
    categories_for_llm = Letter.get_classification_choices_for_llm()

    print(f"=== АНАЛИЗ ПИСЬМА {letter_id} ===")
    print(f"Категории для LLM: {categories_for_llm}")

    # Подготавливаем текст для анализа
    text_to_analyze = f"""
    ОТПРАВИТЕЛЬ: {letter.sender}
    ТЕМА: {letter.subject}
    ТЕКСТ ПИСЬМА:
    {letter.original_text}
    """

    # Анализируем - передаем категории в метод analyze_letter
    analysis_result = llm_client.analyze_letter(text_to_analyze, categories_for_llm)

    # Обновляем письмо - данные уже сконвертированы
    letter.summary = analysis_result['summary']
    letter.classification = analysis_result['classification']
    letter.criticality_level = analysis_result['criticality_level']
    letter.response_style = analysis_result['response_style']
    letter.processing_time_hours = analysis_result['processing_time_hours']

    # Парсим дедлайн
    from django.utils.dateparse import parse_datetime
    sla_deadline_str = analysis_result['sla_deadline']
    if sla_deadline_str:
        try:
            letter.sla_deadline = parse_datetime(sla_deadline_str)
        except (ValueError, TypeError):
            # Если не удалось распарсить, используем расчет по часам
            from datetime import timedelta
            letter.sla_deadline = timezone.now() + timedelta(
                hours=letter.processing_time_hours
            )

    letter.status = 'analyzed'
    letter.save()

    # Сохраняем полный анализ
    AnalysisResult.objects.create(
        letter=letter,
        analysis_data=analysis_result
    )

    return redirect('analysis_results', letter_id=letter.id)


def analysis_results(request, letter_id):
    """Просмотр результатов анализа с ссылками на вопросы и генерацию ответов"""
    letter = get_object_or_404(Letter, id=letter_id)

    from datetime import timedelta
    time_threshold = timezone.now() + timedelta(hours=24)

    try:
        analysis_result = AnalysisResult.objects.get(letter=letter)
        analysis_data = analysis_result.analysis_data
    except AnalysisResult.DoesNotExist:
        analysis_data = {}

    # Проверяем, есть ли вопросы к этому письму
    has_questions = LetterQuestion.objects.filter(letter=letter).exists()

    context = {
        'letter': letter,
        'analysis': analysis_data,
        'has_questions': has_questions,
        'now': timezone.now(),
        'time_threshold': time_threshold,
    }

    return render(request, 'analysis_results.html', context)


def generate_responses(request, letter_id):
    """Генерация вариантов ответов с улучшенной обработкой ошибок"""
    letter = get_object_or_404(Letter, id=letter_id)

    # Если письмо еще не анализировалось, перенаправляем на анализ
    if letter.status == 'new':
        return redirect('analyze_letter', letter_id=letter.id)

    # Обработка сброса и генерации нового ответа - ДОБАВЛЕНО ПОЛНОЕ ОЧИЩЕНИЕ
    if request.method == 'POST' and 'reset' in request.POST:
        # Удаляем существующие ответы
        GeneratedResponse.objects.filter(letter=letter).delete()
        # Сбрасываем финальный ответ и связанные поля
        letter.final_response = ''
        letter.response_style = None
        letter.status = 'analyzed'  # Возвращаем статус к анализированному
        letter.save()

        messages.success(request, "Старый ответ удален. Вы можете сгенерировать новый ответ.")
        return redirect('generate_responses', letter_id=letter.id)

    # Обработка выбора существующего ответа
    if request.method == 'POST' and 'selected_response' in request.POST:
        selected_response_id = request.POST.get('selected_response')
        try:
            # Сбрасываем все выбранные ответы
            GeneratedResponse.objects.filter(letter=letter).update(is_selected=False)

            # Устанавливаем выбранный ответ
            selected_response = GeneratedResponse.objects.get(id=selected_response_id, letter=letter)
            selected_response.is_selected = True
            selected_response.save()

            # Сохраняем как финальный ответ
            letter.final_response = selected_response.response_text
            letter.response_style = selected_response.response_style
            letter.status = 'response_generated'
            letter.save()

            messages.success(request, "Ответ выбран как финальный!")
            return redirect('generate_responses', letter_id=letter.id)

        except GeneratedResponse.DoesNotExist:
            messages.error(request, "Выбранный ответ не найден.")

    # Обработка формы генерации нового ответа
    if request.method == 'POST' and 'generate_responses' in request.POST:
        selected_style = request.POST.get('response_style')
        user_commentary = request.POST.get('user_commentary', '').strip()

        if selected_style:
            # Если пожелания пустые, создаем базовое описание
            if not user_commentary:
                user_commentary = f"""
                Краткое содержание письма: {letter.summary}
                Тип письма: {letter.get_classification_display()}
                Уровень критичности: {letter.get_criticality_level_display()}
                """

            try:
                # Генерируем ответ только для выбранного стиля
                response_text = llm_client.generate_response(
                    old_text_email=letter.original_text,
                    user_commentary=user_commentary,
                    style=int(selected_style)
                )

                # Удаляем старые ответы для этого письма
                GeneratedResponse.objects.filter(letter=letter).delete()

                # Создаем новый ответ
                generated_response = GeneratedResponse.objects.create(
                    letter=letter,
                    response_style=int(selected_style),
                    response_text=response_text,
                    is_selected=True  # Помечаем как выбранный сразу
                )

                # Сохраняем финальный ответ в письмо
                letter.final_response = response_text
                letter.status = 'response_generated'
                letter.response_style = int(selected_style)
                letter.save()

                messages.success(request, "Ответ успешно сгенерирован!")
                return redirect('generate_responses', letter_id=letter.id)

            except Exception as e:
                error_message = f"Ошибка при генерации ответа: {str(e)}"
                print(error_message)
                messages.error(request, error_message)
                # Не перенаправляем, остаемся на странице чтобы пользователь мог попробовать снова

    # Получение сгенерированных ответов
    responses = GeneratedResponse.objects.filter(letter=letter)

    # Создаем словарь стилей для шаблона
    response_styles_dict = dict(Letter.RESPONSE_STYLES)

    context = {
        'letter': letter,
        'responses': responses,
        'response_styles': response_styles_dict,
    }

    return render(request, 'generate_response.html', context)


def letter_detail(request, letter_id):
    """Детальная информация о письме"""
    letter = get_object_or_404(Letter, id=letter_id)

    try:
        analysis_result = AnalysisResult.objects.get(letter=letter)
        analysis_data = analysis_result.analysis_data
    except AnalysisResult.DoesNotExist:
        analysis_data = {}

    context = {
        'letter': letter,
        'analysis': analysis_data,
        'now': timezone.now(),
    }

    return render(request, 'letter_detail.html', context)


# Простая версия без AJAX для начала
def update_letter_status(request, letter_id):
    """Обновление статуса письма"""
    letter = get_object_or_404(Letter, id=letter_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in dict(Letter.STATUS_CHOICES):
            letter.status = new_status
            letter.save()

    return redirect('letter_detail', letter_id=letter.id)


def get_letter_statistics(request):
    """Статистика по письмам"""
    total_letters = Letter.objects.count()

    # Статистика по статусам с человекочитаемыми названиями
    status_choices = dict(Letter.STATUS_CHOICES)
    by_status = {}
    for status_value, status_name in status_choices.items():
        count = Letter.objects.filter(status=status_value).count()
        percentage = round((count / total_letters * 100), 1) if total_letters > 0 else 0
        by_status[status_value] = {
            'name': status_name,
            'count': count,
            'percentage': percentage
        }

    # Статистика по классификациям - используем метод модели
    classification_choices = Letter.get_classification_choices()
    by_classification = {}
    for class_value, class_name in classification_choices:
        count = Letter.objects.filter(classification=class_value).count()
        if count > 0:  # Показываем только те, где есть письма
            by_classification[class_value] = {
                'name': class_name,
                'count': count,
                'percentage': round((count / total_letters * 100), 1) if total_letters > 0 else 0
            }

    # Статистика по критичности
    criticality_choices = dict(Letter.CRITICALITY_LEVELS)
    by_criticality = {}
    for crit_value, crit_name in criticality_choices.items():
        count = Letter.objects.filter(criticality_level=crit_value).count()
        if count > 0:  # Показываем только те, где есть письма
            by_criticality[crit_value] = {
                'name': crit_name,
                'count': count,
                'percentage': round((count / total_letters * 100), 1) if total_letters > 0 else 0
            }

    # Статистика по срочности (истекающие сроки)
    time_threshold = timezone.now() + timedelta(hours=24)
    urgent_letters = Letter.objects.filter(
        sla_deadline__isnull=False,
        sla_deadline__lte=time_threshold
    ).count()

    expired_letters = Letter.objects.filter(
        sla_deadline__isnull=False,
        sla_deadline__lt=timezone.now()
    ).count()

    # Исправляем расчет писем "в обработке"
    # Письма в обработке - это все письма кроме завершенных и архивных
    in_progress_letters = Letter.objects.exclude(
        status__in=['done', 'archived']
    ).count()

    context = {
        'total_letters': total_letters,
        'by_status': by_status,
        'by_classification': by_classification,
        'by_criticality': by_criticality,
        'urgent_letters': urgent_letters,
        'expired_letters': expired_letters,
        'in_progress_letters': in_progress_letters,  # Добавляем правильный счетчик
        'urgent_percentage': round((urgent_letters / total_letters * 100), 1) if total_letters > 0 else 0,
        'expired_percentage': round((expired_letters / total_letters * 100), 1) if total_letters > 0 else 0,
        'in_progress_percentage': round((in_progress_letters / total_letters * 100), 1) if total_letters > 0 else 0,
    }

    return render(request, 'statistics.html', context)


def reset_to_default_categories(request):
    """Сброс категорий к базовым настройкам"""
    if request.method == 'POST':
        # Предупреждение о потере данных
        if Letter.objects.exclude(classification__isnull=True).exists() or AnalysisResult.objects.exists():
            messages.warning(request,
                             "Внимание! Все существующие результаты анализа писем будут удалены "
                             "при сбросе к базовым категориям."
                             )
            return redirect('confirm_classification_reset')

        # Если нет существующих данных, сразу применяем сброс
        return apply_classification_reset(request)

    return redirect('classification_settings')


def confirm_classification_reset(request):
    """Подтверждение сброса классификаторов"""
    if request.method == 'POST':
        if 'confirm' in request.POST:
            return apply_classification_reset(request)
        else:
            return redirect('classification_settings')

    # Подсчет данных для удаления
    letters_count = Letter.objects.exclude(classification__isnull=True).count()
    analysis_count = AnalysisResult.objects.count()
    responses_count = GeneratedResponse.objects.count()

    context = {
        'letters_count': letters_count,
        'analysis_count': analysis_count,
        'responses_count': responses_count,
    }
    return render(request, 'confirm_classification_reset.html', context)


def apply_classification_reset(request):
    """Применение сброса к базовым категориям"""
    try:
        with transaction.atomic():
            # Деактивируем все пользовательские категории
            ClassificationCategory.objects.filter(is_active=True).update(is_active=False)

            # Очищаем кэш категорий
            Letter.clear_classification_cache()

            # Удаляем все данные анализа
            AnalysisResult.objects.all().delete()
            GeneratedResponse.objects.all().delete()

            # Сбрасываем классификацию у всех писем
            Letter.objects.all().update(
                classification=None,
                summary='',
                criticality_level=None,
                response_style=None,
                processing_time_hours=None,
                sla_deadline=None,
                final_response='',
                status='new'
            )

            messages.success(request,
                             "Классификаторы успешно сброшены к базовым настройкам! "
                             "Все письма помечены для повторного анализа."
                             )

    except Exception as e:
        messages.error(request, f"Ошибка при сбросе классификаторов: {str(e)}")

    return redirect('classification_settings')


def ask_question(request, letter_id):
    """Страница для задавания вопросов LLM о письме"""
    letter = get_object_or_404(Letter, id=letter_id)

    # Получаем историю вопросов к этому письму
    questions = LetterQuestion.objects.filter(letter=letter).order_by('asked_at')

    if request.method == 'POST':
        question_text = request.POST.get('question', '').strip()

        if question_text:
            # Подготавливаем контекст для LLM
            context = f"""
            ИНФОРМАЦИЯ О ПИСЬМЕ:
            Отправитель: {letter.sender}
            Тема: {letter.subject}
            Текст письма: {letter.original_text}

            РЕЗУЛЬТАТЫ АНАЛИЗА:
            Тип: {letter.get_classification_display()}
            Критичность: {letter.get_criticality_level_display()}
            Краткое содержание: {letter.summary}

            ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question_text}

            Ответь на вопрос пользователя, основываясь на информации о письме.
            Будь точным и полезным.
            """

            try:
                # Используем существующий метод генерации ответа
                answer = llm_client.generate_text(
                    text_email=context,
                    user_commentary=question_text,
                )

                # Сохраняем вопрос и ответ
                LetterQuestion.objects.create(
                    letter=letter,
                    question=question_text,
                    answer=answer
                )

                messages.success(request, "Ответ от LLM получен!")
                return redirect('ask_question', letter_id=letter.id)

            except Exception as e:
                messages.error(request, f"Ошибка при получении ответа: {str(e)}")

    context = {
        'letter': letter,
        'questions': questions,
    }

    return render(request, 'ask_question.html', context)