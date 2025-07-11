FROM python:3.12-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY src/pyproject.toml ./
COPY src/poetry.lock* ./

# Устанавливаем Poetry и зависимости
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Копируем исходный код
COPY src/ ./src/

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 