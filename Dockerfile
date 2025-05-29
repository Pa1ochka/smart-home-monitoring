# Используем легковесный образ Python 3.12 для минимизации размера контейнера
FROM python:3.12-slim

# Устанавливаем рабочую директорию для приложения
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их без кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем утилиту wait-for-it для ожидания зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Копируем код приложения
COPY . .

# Команда запуска будет задана в docker-compose.yml для каждого сервиса