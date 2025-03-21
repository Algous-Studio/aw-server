FROM python:3.9-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы для установки зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем poetry и зависимости без dev-пакетов
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --without dev --no-root


RUN pip install git+https://github.com/ActivityWatch/aw-core.git
# Копируем исходный код проекта
COPY . .

# Если aw-server слушает на определённом порту (например, 5600), открываем его
EXPOSE 5600

# Запускаем сервер
CMD ["python", "-m", "aw_server"]
