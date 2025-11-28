import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    'SECRET_KEY',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'DB_HOST',
    'DB_PORT',
    'FOLDER_ID',
    'API_KEY'
]

print("=== Проверка обязательных переменных окружения ===")
missing_vars = []

for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"{var}: {'*' * len(value) if 'KEY' in var or 'PASSWORD' in var else value}")
    else:
        print(f"{var}: ОТСУТСТВУЕТ")
        missing_vars.append(var)

if missing_vars:
    print(f"\nОшибка: Отсутствуют обязательные переменные: {missing_vars}")
    print("Добавьте их в файл .env")
    exit(1)
else:
    print(f"\nВсе {len(required_vars)} обязательных переменных присутствуют")