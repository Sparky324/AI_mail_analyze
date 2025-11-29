import os
import re
import time
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from bank_letters.services.models import RequestAnalysis, EmailGeneration, TextGeneration
from bank_letters.services.prompts import EMAIL_ANALYSIS_PROMPT, EMAIL_GENERATION_PROMPTS, make_analyze_email_prompt, make_generate_text_prompt
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
        self.data_folder = "data_simple"
        self.vector_store_id = None
        self.vector_store_name = "rag_store_abandoned_1"

        # Настройки таймаутов
        self.timeout_seconds = 30  # Увеличиваем таймаут
        self.max_retries = 2  # Количество попыток

        self.client = OpenAI(
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            api_key=self.api_key,
            project=self.folder_id
        )

        # Инициализация RAG
        self._initialize_rag(self.vector_store_name)

    def make_model(self, model_name):
        return f"gpt://{self.folder_id}/{model_name}"

    def analyze_letter(self, text, categories):
        """Анализ письма с преобразованием результата"""
        model = self.make_model(model_name=YAGPT_MODEL_NAME)

        prompt = make_analyze_email_prompt(categories)

        # Добавляем RAG контекст для лучшего анализа
        rag_query = f"Анализ письма: {text}..."
        rag_context = self._rag_search(rag_query)

        if rag_context:
            prompt += f"\n\nКонтекст для анализа:\n{rag_context}"
            print(f'Контекст от RAG: {rag_context}')
        else:
            print(f'Контекста от RAG не было')

        for attempt in range(self.max_retries + 1):
            try:
                res = self.client.responses.parse(
                    model=model,
                    text_format=RequestAnalysis,
                    instructions=prompt,
                    input=text,
                    timeout=self.timeout_seconds
                )

                # Обрабатываем ответ через процессор
                return self.processor.process_analysis_response(res.output_parsed, categories)

            except Exception as e:
                print(f"Попытка {attempt + 1} не удалась: {e}")
                if attempt < self.max_retries:
                    print("Повторная попытка через 2 секунды...")
                    time.sleep(2)
                else:
                    print("Все попытки не удались, используем ответ по умолчанию")
                    return self.processor.process_analysis_response(None, categories)

    def generate_response(self, old_text_email, user_commentary, style):
        """Генерация ответа в указанном стиле с улучшенной обработкой ошибок"""
        basic_prompt = EMAIL_GENERATION_PROMPTS[style]

        # Всегда гарантируем, что есть какой-то текст
        if not user_commentary or user_commentary.strip() == '':
            user_commentary = "Сгенерируй профессиональный ответ на письмо."

        finished_prompt_text = f'{basic_prompt}\nТекст письма:\n{old_text_email}\n\nДополнительные указания:\n{user_commentary}'

        # Добавляем RAG контекст для лучшего анализа
        rag_query = f"Анализ письма: {old_text_email}..."
        rag_context = self._rag_search(rag_query)

        rag_query_2 = f"Что нужно посмотреть: {user_commentary}..."
        rag_context_2 = self._rag_search(rag_query_2)

        if rag_context or rag_context_2:
            finished_prompt_text += f"\n\nКонтекст для анализа:\n{rag_context}\n{rag_context_2}"
            print(f'Контекст от RAG: {rag_context}\n{rag_context_2}')
        else:
            print(f'Контекста от RAG не было')


        model = self.make_model(model_name=YAGPT_MODEL_NAME)

        # Пробуем основной метод с повторными попытками
        for attempt in range(self.max_retries + 1):
            try:
                print(f"Попытка генерации ответа #{attempt + 1}")
                res = self.client.responses.parse(
                    model=model,
                    text_format=EmailGeneration,
                    instructions="Ты электронный помошник для составления писем.",
                    input=finished_prompt_text,
                    timeout=self.timeout_seconds
                )

                return res.output_parsed.response_email

            except Exception as e:
                print(f"Попытка {attempt + 1} не удалась: {e}")
                if attempt < self.max_retries:
                    wait_time = (attempt + 1) * 3  # Увеличиваем задержку с каждой попыткой
                    print(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    print("Все попытки не удались, используем fallback")
                    # Пробуем альтернативный способ
                    try:
                        return self._generate_response_fallback(finished_prompt_text, model)
                    except Exception as fallback_error:
                        print(f"Fallback также не сработал: {fallback_error}")
                        return self._get_emergency_response(style)

    def generate_text(self, text_email, user_commentary):
        """Генерация текста для помощи в обработке сообщения в указанном стиле"""

        # Всегда гарантируем, что есть какой-то текст
        if not user_commentary or user_commentary.strip() == '':
            user_commentary = "Сгенерируй профессиональный ответ на письмо."

        instructions = make_generate_text_prompt(text_email, user_commentary)

        # Добавляем RAG контекст для лучшего анализа
        rag_query = f"Анализ письма: {text_email}..."
        rag_context = self._rag_search(rag_query)

        rag_query_2 = f"Что нужно сделать: {user_commentary}..."
        rag_context_2 = self._rag_search(rag_query_2)

        finished_context = ""
        if rag_context or rag_context_2:
            finished_context = f"\nКонтекст для составления ответа:\n{rag_context}\n{rag_context_2}"
            print(f'Контекст от RAG: {finished_context}')
        else:
            print(f'Контекста от RAG не было')


        model = self.make_model(model_name=YAGPT_MODEL_NAME)
        try:
            res = self.client.responses.parse(
                model=model,
                text_format=TextGeneration,
                instructions=instructions,
                input=finished_context
            )

            return res.output_parsed.response

        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")

            # Пробуем альтернативный способ - прямой вызов без парсинга
            try:
                return self._generate_response_fallback(instructions + finished_context, model)
            except Exception as fallback_error:
                print(f"Fallback также не сработал: {fallback_error}")
                return f"Не удалось получить ответ."

    def _generate_response_fallback(self, prompt, model):
        """Альтернативный способ генерации ответа с упрощенным запросом"""
        try:
            print("Используем упрощенный fallback метод")

            # Упрощаем промпт для fallback
            simplified_prompt = f"""
            Сгенерируй профессиональный ответ на банковское письмо.

            Текст письма:
            {prompt.split('Текст письма:')[1].split('Дополнительные указания:')[0] if 'Текст письма:' in prompt else prompt}

            Ответ должен быть вежливым и профессиональным.
            """

            # Используем обычный completion вместо parse с меньшим таймаутом
            response = self.client.responses.create(
                model=model,
                instructions="Ты - AI ассистент для генерации ответов на банковские письма. Генерируй профессиональные ответы.",
                input=simplified_prompt,
                timeout=20  # Меньший таймаут для fallback
            )

            # Очищаем ответ от управляющих символов
            clean_text = self._clean_response_text(response.output_text)
            return clean_text

        except Exception as e:
            print(f"Ошибка в fallback методе: {e}")
            raise e

    def _get_emergency_response(self, style):
        """Аварийный ответ когда все методы не сработали"""
        emergency_responses = {
            1: """Уважаемый отправитель,

Благодарим Вас за обращение. Ваше письмо получено и находится в обработке. 
В ближайшее время мы предоставим Вам подробный ответ.

С уважением,
Банк""",

            2: """Уважаемый коллега,

Подтверждаем получение Вашего письма. В настоящее время мы изучаем изложенные вопросы 
и подготовим ответ в установленные сроки.

С наилучшими пожеланиями,
Команда Банка""",

            3: """Уважаемый клиент,

Спасибо за Ваше обращение! Мы получили Ваше письмо и уже начали его обработку.
Наши специалисты изучат Ваш запрос и свяжутся с Вами в ближайшее время.

С заботой о Вас,
Ваш Банк""",

            4: """Получено. В обработке. Ответ будет предоставлен в установленные сроки.

Банк"""
        }

        response = emergency_responses.get(style, emergency_responses[2])
        print("Используем аварийный заготовленный ответ")
        return response

    def _clean_response_text(self, text):
        """Очищает текст от управляющих символов"""
        if not text:
            return "Не удалось сгенерировать ответ."

        # Удаляем управляющие символы (0x00-0x1F), кроме табуляции и переноса строк
        clean_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # Удаляем лишние пробелы
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        return clean_text

    def _initialize_rag(self, vector_store_name):
        """Инициализация RAG системы"""
        try:
            # Создаем или получаем векторное хранилище
            vector_stores = self.client.vector_stores.list()
            existing_store = next((vs for vs in vector_stores.data if vs.name == vector_store_name), None)

            if existing_store:
                self.vector_store_id = existing_store.id
                print(
                    f"Используется существующее векторное хранилище: {vector_store_name} (ID: {self.vector_store_id})")
            else:
                vector_store = self.client.vector_stores.create(name=vector_store_name)
                self.vector_store_id = vector_store.id
                print(f"Создано новое векторное хранилище: {vector_store_name} (ID: {self.vector_store_id})")

            # Загружаем txt файлы из папки data
            self._load_txt_files_to_vector_store()

        except Exception as e:
            print(f"Ошибка при инициализации RAG: {e}")
            self.vector_store_id = None

    def _load_txt_files_to_vector_store(self):
        """Загружает все txt файлы из папки data в векторное хранилище"""
        if not self.vector_store_id:
            print("Vector store не инициализирован, пропускаем загрузку файлов")
            return

        data_path = Path(self.data_folder)
        if not data_path.exists():
            print(f"Папка {self.data_folder} не существует, создаем...")
            data_path.mkdir(parents=True, exist_ok=True)
            return

        # Ищем все txt файлы
        txt_files = list(data_path.glob("**/*.txt"))

        if not txt_files:
            print(f"В папке {self.data_folder} не найдено txt файлов")
            return

        print(f"Найдено {len(txt_files)} txt файлов для загрузки")

        # Загружаем файлы по одному
        successful_uploads = 0
        for file_path in txt_files:
            try:
                print(f"Загружаем файл: {file_path}")

                # Загружаем файл напрямую
                with open(file_path, 'rb') as file:
                    # Создаем файл в OpenAI
                    oai_file = self.client.files.create(
                        file=file,
                        purpose="batch"
                    )

                    # Добавляем файл в векторное хранилище
                    vector_store_file = self.client.vector_stores.files.create(
                        vector_store_id=self.vector_store_id,
                        file_id=oai_file.id
                    )

                    print(f"Успешно загружен: {file_path} (ID файла: {oai_file.id})")
                    successful_uploads += 1

            except Exception as e:
                print(f"Ошибка при загрузке файла {file_path}: {e}")

        print(f"Успешно загружено {successful_uploads} из {len(txt_files)} файлов")

    def _rag_search(self, query, max_results=3):
        """Поиск релевантной информации в векторном хранилище"""
        if not self.vector_store_id:
            print("Vector store не доступен, пропускаем RAG поиск")
            return ""

        try:
            # Используем поиск по векторному хранилищу
            search_results = self.client.vector_stores.search(
                vector_store_id=self.vector_store_id,
                query=query,
                max_num_results=max_results
            )

            if not search_results.data:
                return ""

            # Форматируем результаты
            context_parts = []
            for i, result in enumerate(search_results.data, 1):
                context_text = getattr(result, 'text', getattr(result, 'content', ''))
                if context_text:
                    context_parts.append(f"[Документ {i}]: {context_text}")

            return "\n\n".join(context_parts)
        except Exception as e:
            print(f"Ошибка при RAG поиске: {e}")
            return ""