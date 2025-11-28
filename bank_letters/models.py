from django.db import models


class Letter(models.Model):
    # Классификация (1-6)
    CLASSIFICATION_CHOICES = [
        (1, 'Запрос информации/документов'),
        (2, 'Официальная жалоба или претензия'),
        (3, 'Регуляторный запрос'),
        (4, 'Партнёрское предложение'),
        (5, 'Запрос на согласование'),
        (6, 'Уведомление или информирование'),
    ]

    # Уровень критичности (1-4)
    CRITICALITY_LEVELS = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Критический'),
    ]

    # Стиль ответа (1-4)
    RESPONSE_STYLES = [
        (1, 'Строгий официальный стиль'),
        (2, 'Деловой корпоративный стиль'),
        (3, 'Клиентоориентированный вариант'),
        (4, 'Краткий информационный ответ'),
    ]

    # Статусы письма
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('analyzed', 'Проанализировано'),
        ('response_generated', 'Ответ сгенерирован'),
        ('done', 'Завершено'),
        ('archived', 'В архиве'),
    ]

    # Основные поля
    sender = models.CharField(
        max_length=255,
        verbose_name="Отправитель",
        help_text="ФИО или название организации отправителя"
    )
    subject = models.CharField(
        max_length=500,
        verbose_name="Тема письма",
        help_text="Краткая тема или заголовок письма"
    )
    original_text = models.TextField(verbose_name="Текст письма")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    # Классификация и анализ
    classification = models.IntegerField(
        choices=CLASSIFICATION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Классификация"
    )
    criticality_level = models.IntegerField(
        choices=CRITICALITY_LEVELS,
        null=True,
        blank=True,
        verbose_name="Уровень критичности"
    )
    response_style = models.IntegerField(
        choices=RESPONSE_STYLES,
        null=True,
        blank=True,
        verbose_name="Стиль ответа"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Статус"
    )

    # Дополнительные аналитические поля
    urgency_level = models.CharField(max_length=20, blank=True, verbose_name="Уровень срочности")
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name="Срок ответа (SLA)")
    main_request = models.TextField(blank=True, verbose_name="Суть запроса")

    # JSON поля для структурированных данных
    contact_info = models.JSONField(default=dict, blank=True, verbose_name="Контактная информация")
    legal_references = models.JSONField(default=list, blank=True, verbose_name="Нормативные ссылки")
    requirements = models.JSONField(default=list, blank=True, verbose_name="Требования")
    risks = models.JSONField(default=list, blank=True, verbose_name="Риски")
    required_departments = models.JSONField(default=list, blank=True, verbose_name="Отделы для согласования")

    # Метаданные
    analysis_confidence = models.FloatField(default=0.0, verbose_name="Уверенность анализа")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата обработки")

    class Meta:
        verbose_name = "Письмо"
        verbose_name_plural = "Письма"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Письмо #{self.id} - {self.subject}"

    def get_short_subject(self):
        """Возвращает укороченную тему (первые 50 символов)"""
        if len(self.subject) > 50:
            return self.subject[:47] + '...'
        return self.subject


class AnalysisResult(models.Model):
    letter = models.OneToOneField(Letter, on_delete=models.CASCADE, verbose_name="Письмо")
    analysis_data = models.JSONField(verbose_name="Данные анализа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата анализа")

    class Meta:
        verbose_name = "Результат анализа"
        verbose_name_plural = "Результаты анализа"


class GeneratedResponse(models.Model):
    letter = models.ForeignKey(Letter, on_delete=models.CASCADE, verbose_name="Письмо")
    response_style = models.IntegerField(choices=Letter.RESPONSE_STYLES, verbose_name="Стиль ответа")
    response_text = models.TextField(verbose_name="Текст ответа")
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата генерации")
    is_selected = models.BooleanField(default=False, verbose_name="Выбран для отправки")

    class Meta:
        verbose_name = "Сгенерированный ответ"
        verbose_name_plural = "Сгенерированные ответы"