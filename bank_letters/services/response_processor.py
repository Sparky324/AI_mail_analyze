from .models import RequestAnalysis
from .converters import (
    llm_category_to_classification_choices_model,
    llm_response_style_to_model,
    llm_criticality_level_to_model
)
from datetime import datetime, timedelta
from django.utils import timezone


class ResponseProcessor:
    """Обработчик ответов от LLM для преобразования в формат Django модели"""

    @staticmethod
    def process_analysis_response(llm_response):
        """
        Преобразует ответ от LLM анализа в словарь для Django модели Letter
        """
        if not llm_response:
            return ResponseProcessor._get_fallback_response()

        # Если это Pydantic модель
        if isinstance(llm_response, RequestAnalysis):
            return ResponseProcessor._convert_from_pydantic(llm_response)

        # Если это уже словарь
        if isinstance(llm_response, dict):
            return ResponseProcessor._convert_from_dict(llm_response)

        return ResponseProcessor._get_fallback_response()

    @staticmethod
    def _convert_from_pydantic(pydantic_obj: RequestAnalysis):
        """Преобразует Pydantic модель в словарь для Django"""
        # Конвертируем enum значения в числовые коды для Django модели
        classification = llm_category_to_classification_choices_model(
            pydantic_obj.topic_category
        )
        response_style = llm_response_style_to_model(
            pydantic_obj.response_style
        )
        criticality_level = llm_criticality_level_to_model(
            pydantic_obj.criticality_level
        )

        # Рассчитываем дедлайн на основе времени обработки
        sla_deadline = timezone.now() + timedelta(
            hours=pydantic_obj.processing_time_hours
        )

        return {
            'summary': pydantic_obj.summary,
            'classification': classification,
            'response_style': response_style,
            'criticality_level': criticality_level,
            'processing_time_hours': pydantic_obj.processing_time_hours,
            'sla_deadline': sla_deadline.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def _convert_from_dict(data_dict):
        """Преобразует словарь в нужный формат (на случай если придет сырой dict)"""
        # Если данные уже в правильном формате, возвращаем как есть
        if all(key in data_dict for key in ['summary', 'classification', 'response_style', 'criticality_level']):
            return data_dict

        # Пробуем извлечь данные из возможных структур
        return {
            'summary': data_dict.get('summary', ''),
            'classification': data_dict.get('classification', 1),
            'response_style': data_dict.get('response_style', 2),
            'criticality_level': data_dict.get('criticality_level', 2),
            'processing_time_hours': data_dict.get('processing_time_hours', 24),
            'sla_deadline': data_dict.get('sla_deadline', ''),
        }

    @staticmethod
    def process_generation_response(llm_response):
        """
        Преобразует ответ от LLM генерации в текст письма
        """
        if not llm_response:
            return "Не удалось сгенерировать ответ"

        # Если это Pydantic модель EmailGeneration
        if hasattr(llm_response, 'response_email'):
            return llm_response.response_email

        # Если это словарь
        if isinstance(llm_response, dict):
            return llm_response.get('response_email', 'Не удалось сгенерировать ответ')

        # Если это строка
        if isinstance(llm_response, str):
            return llm_response

        return "Не удалось сгенерировать ответ"

    @staticmethod
    def _get_fallback_response():
        """Запасной вариант на случай ошибки"""
        fallback_deadline = timezone.now() + timedelta(days=3)

        return {
            'summary': 'Автоматический анализ недоступен. Требуется ручная обработка.',
            'classification': 1,  # Запрос информации/документов
            'response_style': 2,  # Деловой корпоративный стиль
            'criticality_level': 2,  # Средний
            'processing_time_hours': 24,
            'sla_deadline': fallback_deadline.strftime("%Y-%m-%d %H:%M"),
        }