from django.db import models
from django.utils import timezone


class Letter(models.Model):
    # Классификация (1-6)
    CLASSIFICATION_CHOICES = [
        (1, 'Запрос информации/документов'),
        (2, 'Официальная жалоба или претензия'),
        (3, 'Регуляторный запрос'),
        (4, 'Партнёрское предложение'),
        (5, 'Запрос на согласование'),
        (6, 'Уведомление или информирование'),
        (7, 'Разное'),
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
    # Основные поля (заполняются пользователем)
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

    # Поля, заполняемые LLM
    summary = models.TextField(
        blank=True,
        verbose_name="Краткое содержание",
        help_text="Краткое содержание письма, сгенерированное нейросетью"
    )
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
    processing_time_hours = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Время на обработку (часы)",
        help_text="Примерное время, необходимое для обработки письма"
    )
    sla_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дедлайн по SLA"
    )

    final_response = models.TextField(
        blank=True,
        verbose_name="Финальный ответ",
        help_text="Текст ответа, который будет отправлен отправителю"
    )

    # Статус письма
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Статус"
    )

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