# models.py
from django.db import models
from django.utils import timezone


class ClassificationCategory(models.Model):
    """Модель для пользовательских категорий классификации"""
    number = models.IntegerField(verbose_name="Номер категории")
    name = models.CharField(max_length=255, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание категории")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категория классификации"
        verbose_name_plural = "Категории классификации"
        ordering = ['number']

    def __str__(self):
        return f"{self.number}. {self.name}"


class Letter(models.Model):
    # Базовые категории (будут использоваться только если нет пользовательских)
    BASE_CLASSIFICATION_CHOICES = [
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
        help_text="Примерное время, необходимое для обработку письма"
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

    def get_classification_display(self):
        """Возвращает отображаемое название классификации"""
        from django.db import connection
        try:
            # Проверяем, есть ли пользовательские категории
            if ClassificationCategory.objects.filter(is_active=True).exists():
                custom_categories = ClassificationCategory.objects.filter(is_active=True)
                for category in custom_categories:
                    if category.number == self.classification:
                        return category.name
            # Если нет пользовательских или не нашли совпадение, используем базовые
            for num, name in self.BASE_CLASSIFICATION_CHOICES:
                if num == self.classification:
                    return name
            return "Не определен"
        except:
            # На случай ошибки БД
            for num, name in self.BASE_CLASSIFICATION_CHOICES:
                if num == self.classification:
                    return name
            return "Не определен"

    @classmethod
    def get_base_classification_choices(cls):
        """Возвращает базовые категории"""
        return cls.BASE_CLASSIFICATION_CHOICES

    @classmethod
    def get_classification_choices(cls):
        """Возвращает актуальные choices для классификации"""
        try:
            # Проверяем, есть ли активные пользовательские категории
            if hasattr(cls, '_classification_choices_cache'):
                return cls._classification_choices_cache

            custom_categories = ClassificationCategory.objects.filter(is_active=True)
            if custom_categories.exists():
                choices = [(cat.number, cat.name) for cat in custom_categories.order_by('number')]
                cls._classification_choices_cache = choices
                return choices
            # Возвращаем базовые категории
            cls._classification_choices_cache = cls.BASE_CLASSIFICATION_CHOICES
            return cls.BASE_CLASSIFICATION_CHOICES
        except:
            # На случай ошибки БД, возвращаем базовые категории
            return cls.BASE_CLASSIFICATION_CHOICES


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