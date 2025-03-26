FROM python:3.9-slim

RUN apt-get update && apt-get install -y git make nodejs npm && rm -rf /var/lib/apt/lists/*
# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы для установки зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем poetry и зависимости без dev-пакетов
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --without dev --no-root


RUN pip install git+https://github.com/ActivityWatch/aw-core.git


# Устанавливаем Gunicorn (если не добавлен в зависимости)
RUN pip install gunicorn

# Если нужен web‑интерфейс, можно его собрать (опционально)
ENV SKIP_WEBUI=true
RUN if [ "$SKIP_WEBUI" != "true" ]; then \
      make aw-webui; \
    else \
      echo "Skipping webui build"; \
    fi
    

    # Копируем исходный код проекта
COPY . .
COPY ./aw-webui /app/aw-webui
# Если aw-server слушает на определённом порту (например, 5600), открываем его
EXPOSE 5600

# Запускаем сервер
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5600", "wsgi:app"]

