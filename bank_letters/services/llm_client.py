import requests
import os
from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI
from models import RequestAnalysis
from prompts import EMAIL_ANALYSIS_PROMPT
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

BASE_LLM_URL = 'https://rest-assistant.api.cloud.yandex.net/v1'
QWEN3_235B_MODEL_NAME = 'qwen3-235b-a22b-fp8/latest'
YAGPT_MODEL_NAME = 'yandexgpt/rc'

class LLMClient:
    def __init__(self):
        load_dotenv()
        self.folder_id = os.environ['folder_id']
        self.api_key = os.environ['api_key']
        self.api_url = settings.LLM_API_URL

    def make_model(self, model_name):
        return f"gpt://{self.folder_id}/{model_name}"

    # Запрос к API нейросети для анализа письма
    def analyze_email(self, text):
        model = self.make_model(model_name=YAGPT_MODEL_NAME)
        client = OpenAI(
            base_url = "https://rest-assistant.api.cloud.yandex.net/v1",
            api_key = self.api_key, project = self.folder_id)

        try:
            response = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content=EMAIL_ANALYSIS_PROMPT),
                    ChatCompletionUserMessageParam(role="user", content=text)
                ],
                response_format=RequestAnalysis,
                temperature=0.1
            )

            return response.choices[0].message.parsed
        except Exception as e:
            print(f"Ошибка при анализе запроса: {e}")

    def generate_responses(self, letter_analysis):
        # Генерация вариантов ответов
        pass



