from pydantic import BaseModel, Field
from enum import Enum

# Определение стилей ответа
class ResponseStyle(str, Enum):
    OFFICIAL = 'Строгий официальный стиль'
    CORPORATE = 'Деловой корпоративный стиль'
    CLIENT = 'Клиентоориентированный вариант'
    INFORMATION =  'Краткий информационный ответ'

# Определение уровней критичности
class CriticalityLevel(str, Enum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Критичный"

class RequestAnalysis(BaseModel):
    topic_category: str = Field(
        description="Классификация темы письма по категориям, одна из перечисленных"
    )
    response_style: ResponseStyle = Field(
        description="Предпочтительный стиль ответа"
    )
    processing_time_hours: int = Field(
        ge=1,
        le=720,
        description="Время на обработку в часах согласно регламенту"
    )
    criticality_level: CriticalityLevel = Field(
        description="Уровень критичности запроса"
    )
    summary: str = Field(
        max_length=500,
        description="Краткое содержание запроса"
    )

class EmailGeneration(BaseModel):
    response_email: str = Field(
        max_length=10000,
        description="Сгенерированное ответное письмо"
    )

class TextGeneration(BaseModel):
    response: str = Field(
        max_length=10000,
        description="Сгенерированный ответ, который попросил пользователь"
    )