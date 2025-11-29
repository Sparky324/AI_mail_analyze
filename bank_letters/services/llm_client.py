# llm_client.py - исправленная версия
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from bank_letters.services.models import RequestAnalysis, EmailGeneration
from bank_letters.services.prompts import EMAIL_ANALYSIS_PROMPT, EMAIL_GENERATION_PROMPTS, make_analyze_email_prompt
from .response_processor import ResponseProcessor

BASE_LLM_URL = 'https://rest-assistant.api.cloud.yandex.net/v1'
QWEN3_235B_MODEL_NAME = 'qwen3-235b-a22b-fp8/latest'
YAGPT_MODEL_NAME = 'yandexgpt/rc'


class LLMClient:
    def __init__(self):
        load_dotenv()
        self.folder_id = os.getenv('folder_id')
        self.api_key = os.getenv('api_key')
        self.api_url = BASE_LLM_URL
        self.processor = ResponseProcessor()

        self.client = OpenAI(
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            api_key=self.api_key,
            project=self.folder_id
        )

    def make_model(self, model_name):
        return f"gpt://{self.folder_id}/{model_name}"

    def analyze_letter(self, text, categories):
        """Анализ письма с преобразованием результата"""
        model = self.make_model(model_name=YAGPT_MODEL_NAME)

        prompt = make_analyze_email_prompt(categories)
        print("Промпт для анализа:")
        print(prompt)
        print("Категории:", categories)

        try:
            res = self.client.responses.parse(
                model=model,
                text_format=RequestAnalysis,
                instructions=prompt,
                input=text
            )

            # Обрабатываем ответ через процессор
            return self.processor.process_analysis_response(res.output_parsed, categories)

        except Exception as e:
            print(f"Ошибка при анализе запроса: {e}")
            return self.processor.process_analysis_response(None, categories)

    def generate_response(self, old_text_email, user_commentary, style):
        """Генерация ответа в указанном стиле"""
        basic_prompt = EMAIL_GENERATION_PROMPTS[style]

        # Всегда гарантируем, что есть какой-то текст
        if not user_commentary or user_commentary.strip() == '':
            user_commentary = "Сгенерируй профессиональный ответ на письмо."

        finished_prompt_text = f'{basic_prompt}\nТекст письма:\n{old_text_email}\n\nДополнительные указания:\n{user_commentary}'

        model = self.make_model(model_name=YAGPT_MODEL_NAME)
        try:
            res = self.client.responses.parse(
                model=model,
                text_format=EmailGeneration,
                instructions=finished_prompt_text,
                input=finished_prompt_text
            )

            return res.output_parsed.response_email

        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")

            # Пробуем альтернативный способ - прямой вызов без парсинга
            try:
                return self._generate_response_fallback(finished_prompt_text, model)
            except Exception as fallback_error:
                print(f"Fallback также не сработал: {fallback_error}")
                return f"Автоматический ответ: Благодарим за обращение. Ваше письмо получено и находится в обработке. С уважением, Банк."

    def _generate_response_fallback(self, prompt, model):
        """Альтернативный способ генерации ответа"""
        try:
            # Используем обычный completion вместо parse
            response = self.client.responses.create(
                model=model,
                instructions="Ты - AI ассистент для генерации ответов на банковские письма. Генерируй профессиональные ответы.",
                input=prompt
            )

            # Очищаем ответ от управляющих символов
            clean_text = self._clean_response_text(response.output_text)
            return clean_text

        except Exception as e:
            print(f"Ошибка в fallback методе: {e}")
            raise e

    def _clean_response_text(self, text):
        """Очищает текст от управляющих символов"""
        if not text:
            return "Не удалось сгенерировать ответ."

        # Удаляем управляющие символы (0x00-0x1F), кроме табуляции и переноса строк
        clean_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # Удаляем лишние пробелы
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return clean_text