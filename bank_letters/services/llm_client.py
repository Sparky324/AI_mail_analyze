import os
from dotenv import load_dotenv
from openai import OpenAI
from bank_letters.services.models import RequestAnalysis, EmailGeneration
from bank_letters.services.prompts import EMAIL_ANALYSIS_PROMPT, EMAIL_GENERATION_PROMPTS
from .response_processor import ResponseProcessor

BASE_LLM_URL = 'https://rest-assistant.api.cloud.yandex.net/v1'
QWEN3_235B_MODEL_NAME = 'qwen3-235b-a22b-fp8/latest'
YAGPT_MODEL_NAME = 'yandexgpt/rc'


class LLMClient:
    def __init__(self):
        load_dotenv()
        self.folder_id = os.getenv('FOLDER_ID')
        self.api_key = os.getenv('API_KEY')
        self.api_url = BASE_LLM_URL
        self.processor = ResponseProcessor()

        self.client = OpenAI(
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            api_key=self.api_key,
            project=self.folder_id
        )

    def make_model(self, model_name):
        return f"gpt://{self.folder_id}/{model_name}"

    def analyze_letter(self, text):
        """Анализ письма с преобразованием результата"""
        model = self.make_model(model_name=YAGPT_MODEL_NAME)

        try:
            res = self.client.responses.parse(
                model=model,
                text_format=RequestAnalysis,
                instructions=EMAIL_ANALYSIS_PROMPT,
                input=text
            )

            # Обрабатываем ответ через процессор
            return self.processor.process_analysis_response(res.output_parsed)

        except Exception as e:
            print(f"Ошибка при анализе запроса: {e}")
            return self.processor.process_analysis_response(None)

    def generate_response(self, old_text_email, user_commentary, style):
        """Генерация ответа с преобразованием результата"""
        basic_prompt = EMAIL_GENERATION_PROMPTS[style]
        finished_prompt_text = f'{basic_prompt}\nТекст письма, на которое нужно ответить:\n{old_text_email}\n\nКомментарии пользователя, на основе которых надо написать ответное письмо:\n{user_commentary}'

        model = self.make_model(model_name=YAGPT_MODEL_NAME)
        try:
            res = self.client.responses.parse(
                model=model,
                text_format=EmailGeneration,
                instructions=finished_prompt_text,
                input=finished_prompt_text
            )

            # Обрабатываем сгенерированный ответ
            return self.processor.process_generation_response(res.output_parsed)

        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")
            return self.processor.process_generation_response(None)