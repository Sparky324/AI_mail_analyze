from pydantic import BaseModel, Field
from enum import Enum

class TopicCategory(str, Enum):
    INFORMATION_REQUEST = 'Запрос информации/документов'
    COMPLAINT = 'Официальная жалоба или претензия'
    GOVERNMENT_REQUEST = 'Регуляторный запрос'
    PARTNER_DEAL =  'Партнёрское предложение'
    APPROVAL_REQUEST =  'Запрос на согласование'
    NOTICE =  'Уведомление или информирование'
    OTHER = "Другое"

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
    topic_category: TopicCategory = Field(
        description="Классификация темы по категориям"
    )
    response_style: ResponseStyle = Field(
        description="Предпочтительный стиль ответа"
    )
    processing_time_hours: float = Field(
        ge=0.1,
        le=1720,
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