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

    # Фильтрация по статусу (если передана в GET параметре)
    status_filter = request.GET.get('status')
    if status_filter:
        letters = letters.filter(status=status_filter)

    # Фильтрация по классификации
    classification_filter = request.GET.get('classification')
    if classification_filter:
        letters = letters.filter(classification=classification_filter)

    context = {
        'letters': letters,
        'status_choices': Letter.STATUS_CHOICES,
        'classification_choices': Letter.CLASSIFICATION_CHOICES,
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

    # Если письмо уже анализировалось, показываем результаты
    if letter.status != 'new':
        return redirect('analysis_results', letter_id=letter.id)

    # Анализ текста нейросетью
    llm_client = LLMClient()

    # Подготавливаем текст для анализа (включая отправителя и тему)
    text_to_analyze = f"""
    ОТПРАВИТЕЛЬ: {letter.sender}
    ТЕМА: {letter.subject}
    ТЕКСТ ПИСЬМА:
    {letter.original_text}
    """

    # Вызываем анализ нейросети (пока используем мок-данные)
    analysis_result = llm_client.analyze_letter(text_to_analyze)

    # Обновляем письмо данными анализа
    letter.classification = analysis_result.get('classification', 1)
    letter.criticality_level = analysis_result.get('criticality_level', 2)
    letter.response_style = analysis_result.get('response_style', 2)
    letter.status = 'analyzed'
    letter.urgency_level = analysis_result.get('urgency_level', 'medium')
    letter.main_request = analysis_result.get('main_request', '')
    letter.contact_info = analysis_result.get('contact_info', {})
    letter.legal_references = analysis_result.get('legal_references', [])
    letter.requirements = analysis_result.get('requirements', [])
    letter.risks = analysis_result.get('risks', [])
    letter.required_departments = analysis_result.get('required_departments', [])
    letter.analysis_confidence = analysis_result.get('confidence', 0.0)
    letter.processed_at = timezone.now()

    # Обработка SLA дедлайна
    sla_deadline = analysis_result.get('sla_deadline')
    if sla_deadline:
        # Здесь может быть логика преобразования строки в datetime
        letter.sla_deadline = timezone.now() + timezone.timedelta(days=3)  # Пример

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
        'departments': letter.required_departments or []
    }

    return render(request, 'analysis_results.html', context)


def generate_responses(request, letter_id):
    """Генерация вариантов ответов"""
    letter = get_object_or_404(Letter, id=letter_id)

    # Если письмо еще не анализировалось, перенаправляем на анализ
    if letter.status == 'new':
        return redirect('analyze_letter', letter_id=letter.id)

    # Генерация ответов при GET запросе или если ответов еще нет
    if request.method == 'GET' and not GeneratedResponse.objects.filter(letter=letter).exists():
        llm_client = LLMClient()

        # Генерируем ответы для всех стилей
        for style_id, style_name in Letter.RESPONSE_STYLES:
            # Временные мок-ответы (замените на реальную генерацию)
            response_text = f"""
            Уважаемый {letter.sender},

            Это тестовый ответ в стиле {style_name}.

            По вашему запросу "{letter.subject}" мы подготовили следующую информацию:
            {letter.main_request}

            С уважением,
            Банк
            """

            GeneratedResponse.objects.create(
                letter=letter,
                response_style=style_id,
                response_text=response_text
            )

        # Обновляем статус письма
        letter.status = 'response_generated'
        letter.save()

    # Получение сгенерированных ответов
    responses = GeneratedResponse.objects.filter(letter=letter)

    # Обработка выбора ответа
    if request.method == 'POST':
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

            # Обновляем статус письма
            letter.status = 'done'
            letter.save()

            return redirect('letter_list')

    context = {
        'letter': letter,
        'responses': responses,
        'response_styles': dict(Letter.RESPONSE_STYLES)
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

    responses = GeneratedResponse.objects.filter(letter=letter)

    context = {
        'letter': letter,
        'analysis': analysis_data,
        'responses': responses,
        'response_styles': dict(Letter.RESPONSE_STYLES)
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


# Временная заглушка для статистики
def get_letter_statistics(request):
    """Статистика по письмам"""
    total_letters = Letter.objects.count()
    by_status = {
        status: Letter.objects.filter(status=status).count()
        for status in dict(Letter.STATUS_CHOICES)
    }

    context = {
        'total_letters': total_letters,
        'by_status': by_status,
    }

    return render(request, 'statistics.html', context)