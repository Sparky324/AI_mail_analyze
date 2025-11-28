# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .forms import LetterUploadForm
from .models import Letter, AnalysisResult, GeneratedResponse
from .services.llm_client import LLMClient


def letter_list(request):
    """Главная страница - список всех писем"""
    letters = Letter.objects.all().order_by('-uploaded_at')

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

    # Получаем текстовые представления для отображения
    status_choices = dict(Letter.STATUS_CHOICES)
    classification_choices = dict(Letter.CLASSIFICATION_CHOICES)

    context = {
        'letters': letters,
        'status_choices': status_choices.items(),
        'classification_choices': classification_choices.items(),
        'now': timezone.now(),  # для сравнения с дедлайнами
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

    llm_client = LLMClient()

    # Подготавливаем текст для анализа
    text_to_analyze = f"""
    ОТПРАВИТЕЛЬ: {letter.sender}
    ТЕМА: {letter.subject}
    ТЕКСТ ПИСЬМА:
    {letter.original_text}
    """

    # Анализируем - получаем уже готовый словарь в правильном формате
    analysis_result = llm_client.analyze_letter(text_to_analyze)

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
    """Просмотр результатов анализа"""
    letter = get_object_or_404(Letter, id=letter_id)

    try:
        analysis_result = AnalysisResult.objects.get(letter=letter)
        analysis_data = analysis_result.analysis_data
    except AnalysisResult.DoesNotExist:
        analysis_data = {}

    context = {
        'letter': letter,
        'analysis': analysis_data,
    }

    return render(request, 'analysis_results.html', context)


def generate_responses(request, letter_id):
    """Генерация вариантов ответов с возможностью выбора стиля и пожеланий"""
    letter = get_object_or_404(Letter, id=letter_id)

    # Если письмо еще не анализировалось, перенаправляем на анализ
    if letter.status == 'new':
        return redirect('analyze_letter', letter_id=letter.id)

    # Обработка сброса и генерации нового ответа
    if request.method == 'POST' and 'reset' in request.POST:
        # Удаляем существующие ответы
        GeneratedResponse.objects.filter(letter=letter).delete()
        # Сбрасываем статус
        letter.status = 'analyzed'
        letter.save()
        return redirect('generate_responses', letter_id=letter.id)

    # Обработка формы выбора стиля и пожеланий
    if request.method == 'POST' and 'generate_responses' in request.POST:
        selected_style = request.POST.get('response_style')
        user_commentary = request.POST.get('user_commentary', '').strip()

        if selected_style:
            llm_client = LLMClient()

            # Если пожелания пустые, создаем базовое описание
            if not user_commentary:
                user_commentary = f"""
                Краткое содержание письма: {letter.summary}
                Тип письма: {letter.get_classification_display()}
                Уровень критичности: {letter.get_criticality_level_display()}
                """

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
                response_text=response_text
            )

            # Помечаем как выбранный
            generated_response.is_selected = True
            generated_response.save()

            # Сохраняем финальный ответ в письмо
            letter.final_response = response_text
            letter.status = 'response_generated'
            letter.response_style = int(selected_style)
            letter.save()

            return redirect('generate_responses', letter_id=letter.id)

    # Обработка выбора готового ответа
    if request.method == 'POST' and 'selected_response' in request.POST:
        selected_response_id = request.POST.get('selected_response')
        if selected_response_id:
            # Сбрасываем все выбранные ответы
            GeneratedResponse.objects.filter(letter=letter).update(is_selected=False)

            # Устанавливаем выбранный ответ
            selected_response = GeneratedResponse.objects.get(
                id=selected_response_id,
                letter=letter
            )
            selected_response.is_selected = True
            selected_response.save()

            # Сохраняем финальный ответ в письмо
            letter.final_response = selected_response.response_text
            letter.response_style = selected_response.response_style
            letter.status = 'done'
            letter.save()

            return redirect('letter_detail', letter_id=letter.id)

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

    # Статистика по классификациям
    classification_choices = dict(Letter.CLASSIFICATION_CHOICES)
    by_classification = {}
    for class_value, class_name in classification_choices.items():
        count = Letter.objects.filter(classification=class_value).count()
        if count > 0:  # Показываем только те, где есть письма
            by_classification[class_value] = {
                'name': class_name,
                'count': count
            }

    # Статистика по критичности
    criticality_choices = dict(Letter.CRITICALITY_LEVELS)
    by_criticality = {}
    for crit_value, crit_name in criticality_choices.items():
        count = Letter.objects.filter(criticality_level=crit_value).count()
        if count > 0:  # Показываем только те, где есть письма
            by_criticality[crit_value] = {
                'name': crit_name,
                'count': count
            }

    context = {
        'total_letters': total_letters,
        'by_status': by_status,
        'by_classification': by_classification,
        'by_criticality': by_criticality,
    }

    return render(request, 'statistics.html', context)