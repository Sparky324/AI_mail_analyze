import requests
from django.conf import settings


class LLMClient:
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.api_key = settings.LLM_API_KEY

    def analyze_letter(self, text):
        # Запрос к API нейросети для анализа письма
        response = requests.post(
            self.api_url,
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={'prompt': f'Проанализируй текст: {text}'}
        )
        return response.json()

    def generate_responses(self, letter_analysis):
        # Генерация вариантов ответов
        pass