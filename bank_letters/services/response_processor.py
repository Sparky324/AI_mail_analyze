# response_processor.py - исправляем для работы с Pydantic моделью
class ResponseProcessor:
    def process_analysis_response(self, parsed_response, categories):
        """Обрабатывает ответ анализа с учетом категорий"""
        # print(f"=== ОБРАБОТКА ОТВЕТА ОТ LLM ===")
        # print(f"Полученный ответ: {parsed_response}")
        # print(f"Тип ответа: {type(parsed_response)}")
        # print(f"Доступные категории: {categories}")

        if parsed_response is None:
            print("ОШИБКА: parsed_response is None, используем ответ по умолчанию")
            return self._get_default_response(categories)

        try:
            # Обрабатываем classification - используем атрибуты объекта
            classification = self._extract_classification(parsed_response, categories)
            criticality_level = self._extract_criticality_level(parsed_response)
            response_style = self._extract_response_style(parsed_response)
            processing_time_hours = self._extract_processing_time(parsed_response)
            sla_deadline = self._extract_sla_deadline(parsed_response)
            summary = self._extract_summary(parsed_response)

            result = {
                'classification': classification,
                'criticality_level': criticality_level,
                'response_style': response_style,
                'processing_time_hours': processing_time_hours,
                'sla_deadline': sla_deadline,
                'summary': summary,
            }

            # print(f"Финальный результат: {result}")
            # print("===============================")

            return result

        except Exception as e:
            print(f"ОШИБКА при обработке ответа анализа: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_response(categories)

    def _extract_classification(self, parsed_response, categories):
        """Извлекает и преобразует classification из Pydantic модели"""
        try:
            # Пробуем разные возможные названия полей
            classification = None

            # Пробуем topic_category (из вашего примера)
            if hasattr(parsed_response, 'topic_category'):
                classification = parsed_response.topic_category
                #print(f"Найдено поле topic_category: {classification}")

            # Пробуем classification
            elif hasattr(parsed_response, 'classification'):
                classification = parsed_response.classification
                #print(f"Найдено поле classification: {classification}")

            # Пробуем category
            elif hasattr(parsed_response, 'category'):
                classification = parsed_response.category
                #print(f"Найдено поле category: {classification}")

            #print(f"Извлеченная классификация: {classification}")
            #print(f"Тип классификации: {type(classification)}")

            # Если classification - число, используем как есть
            if isinstance(classification, int):
                #print(f"Классификация как число: {classification}")
                valid_classifications = [cat['id'] for cat in categories]
                if classification in valid_classifications:
                    return classification

            # Если classification - строка, пытаемся найти соответствие
            if isinstance(classification, str):
                # print(f"Классификация как строка: '{classification}'")
                # Ищем по названию категории
                for cat in categories:
                    if cat['name'].lower() in classification.lower() or classification.lower() in cat['name'].lower():
                        # print(f"Найдено соответствие: '{classification}' -> {cat['id']} ({cat['name']})")
                        return cat['id']

                # Пробуем извлечь число из строки
                import re
                numbers = re.findall(r'\d+', classification)
                if numbers:
                    classification_num = int(numbers[0])
                    valid_classifications = [cat['id'] for cat in categories]
                    if classification_num in valid_classifications:
                        #print(f"Извлечено число из строки: {classification_num}")
                        return classification_num

            # Если не нашли, используем первую категорию
            default_classification = categories[0]['id'] if categories else 1
            #print(f"Не удалось определить классификацию, используем по умолчанию: {default_classification}")
            return default_classification

        except Exception as e:
            print(f"Ошибка при извлечении classification: {e}")
            return categories[0]['id'] if categories else 1

    def _extract_criticality_level(self, parsed_response):
        """Извлекает и преобразует criticality_level из Pydantic модели"""
        try:
            criticality = None

            if hasattr(parsed_response, 'criticality_level'):
                criticality = parsed_response.criticality_level
                #print(f"Найдено поле criticality_level: {criticality}")

            #print(f"Извлеченная критичность: {criticality}")

            if isinstance(criticality, int):
                return max(1, min(4, criticality))  # Ограничиваем диапазон 1-4

            if isinstance(criticality, str):
                criticality_lower = criticality.lower()
                if 'низк' in criticality_lower or 'low' in criticality_lower or '1' in criticality:
                    return 1
                elif 'средн' in criticality_lower or 'medium' in criticality_lower or '2' in criticality:
                    return 2
                elif 'высок' in criticality_lower or 'high' in criticality_lower or '3' in criticality:
                    return 3
                elif 'критич' in criticality_lower or 'critical' in criticality_lower or '4' in criticality:
                    return 4

            return 2  # По умолчанию средний

        except Exception as e:
            #print(f"Ошибка при извлечении criticality_level: {e}")
            return 2

    def _extract_response_style(self, parsed_response):
        """Извлекает и преобразует response_style из Pydantic модели"""
        try:
            style = None

            if hasattr(parsed_response, 'response_style'):
                style = parsed_response.response_style
                #print(f"Найдено поле response_style: {style}")

            #print(f"Извлеченный стиль ответа: {style}")

            if isinstance(style, int):
                return max(1, min(4, style))  # Ограничиваем диапазон 1-4

            if isinstance(style, str):
                style_lower = style.lower()
                if 'официал' in style_lower or 'строг' in style_lower or '1' in style:
                    return 1
                elif 'делов' in style_lower or 'корпоратив' in style_lower or '2' in style:
                    return 2
                elif 'клиент' in style_lower or 'ориентир' in style_lower or '3' in style:
                    return 3
                elif 'кратк' in style_lower or 'информац' in style_lower or '4' in style:
                    return 4

            return 2  # По умолчанию деловой стиль

        except Exception as e:
            print(f"Ошибка при извлечении response_style: {e}")
            return 2


    def _extract_summary(self, parsed_response):
        """Извлекает summary из Pydantic модели"""
        try:
            if hasattr(parsed_response, 'summary'):
                summary = parsed_response.summary
                #print(f"Найдено поле summary: {summary}")
                return str(summary) if summary else 'Не удалось сгенерировать краткое содержание.'
            return 'Не удалось сгенерировать краткое содержание.'
        except Exception as e:
            print(f"Ошибка при извлечении summary: {e}")
            return 'Не удалось сгенерировать краткое содержание.'

    def _get_default_response(self, categories):
        """Возвращает ответ по умолчанию"""
        default_classification = categories[0]['id'] if categories else 1
        #print(f"Используется категория по умолчанию: {default_classification}")

        from django.utils import timezone
        from datetime import timedelta

        default_deadline = timezone.now() + timedelta(hours=24)

        return {
            'classification': default_classification,
            'criticality_level': 1,
            'response_style': 2,
            'processing_time_hours': 24,
            'sla_deadline': default_deadline.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': 'Автоматический анализ не выполнен. Требуется ручная обработка.',
        }

    def _extract_sla_deadline(self, parsed_response):
        """Извлекает sla_deadline из Pydantic модели"""
        try:
            if hasattr(parsed_response, 'sla_deadline'):
                deadline = parsed_response.sla_deadline
                print(f"Найдено поле sla_deadline: {deadline}")
                if deadline and str(deadline).strip():
                    return str(deadline)

            # Если дедлайн не пришел от LLM, рассчитываем его автоматически
            return self._calculate_sla_deadline(parsed_response)

        except Exception as e:
            print(f"Ошибка при извлечении sla_deadline: {e}")
            return self._calculate_sla_deadline(parsed_response)

    def _calculate_sla_deadline(self, parsed_response):
        """Автоматически рассчитывает дедлайн на основе criticality_level"""
        try:
            from django.utils import timezone
            from datetime import timedelta

            # Получаем уровень критичности
            criticality_level = self._extract_criticality_level(parsed_response)

            # Рассчитываем дедлайн в зависимости от критичности
            if criticality_level == 1:  # Низкий
                hours_to_add = 48
            elif criticality_level == 2:  # Средний
                hours_to_add = 24
            elif criticality_level == 3:  # Высокий
                hours_to_add = 8
            else:  # Критический (4) или по умолчанию
                hours_to_add = 4

            deadline = timezone.now() + timedelta(hours=hours_to_add)
            formatted_deadline = deadline.strftime('%Y-%m-%d %H:%M:%S')

            print(
                f"Рассчитан автоматический дедлайн: {formatted_deadline} (критичность: {criticality_level}, +{hours_to_add} часов)")

            return formatted_deadline

        except Exception as e:
            print(f"Ошибка при расчете дедлайна: {e}")
            from django.utils import timezone
            from datetime import timedelta
            default_deadline = timezone.now() + timedelta(hours=24)
            return default_deadline.strftime('%Y-%m-%d %H:%M:%S')

    def _extract_processing_time(self, parsed_response):
        """Извлекает processing_time_hours из Pydantic модели"""
        try:
            processing_time = None

            if hasattr(parsed_response, 'processing_time_hours'):
                processing_time = parsed_response.processing_time_hours
                print(f"Найдено поле processing_time_hours: {processing_time}")

            # Если время обработки не указано или всегда 24, рассчитываем автоматически
            if not processing_time or processing_time == 24:
                return self._calculate_processing_time(parsed_response)

            return int(processing_time)

        except Exception as e:
            print(f"Ошибка при извлечении processing_time_hours: {e}")
            return self._calculate_processing_time(parsed_response)

    def _calculate_processing_time(self, parsed_response):
        """Автоматически рассчитывает время обработки на основе criticality_level"""
        try:
            criticality_level = self._extract_criticality_level(parsed_response)

            # Рассчитываем время обработки в зависимости от критичности
            if criticality_level == 1:  # Низкий
                processing_time = 48
            elif criticality_level == 2:  # Средний
                processing_time = 24
            elif criticality_level == 3:  # Высокий
                processing_time = 8
            else:  # Критический (4)
                processing_time = 4

            print(
                f"Рассчитано автоматическое время обработки: {processing_time} часов (критичность: {criticality_level})")

            return processing_time

        except Exception as e:
            print(f"Ошибка при расчете времени обработки: {e}")
            return 24  # По умолчанию