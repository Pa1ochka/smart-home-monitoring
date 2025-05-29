# Сборка Go-приложения
FROM golang:1.24.3 AS builder

# Рабочая директория для сборки
WORKDIR /app

# Кэширование зависимостей Go
COPY sensor_generator/go.mod sensor_generator/go.sum ./
RUN go mod download

# Копирование исходного кода
COPY sensor_generator/main.go .

# Компиляция бинарного файла
RUN CGO_ENABLED=0 GOOS=linux go build -o sensor_generator main.go

# Минимальный образ для запуска
FROM alpine:3.20

# Установка утилит для ожидания сервисов
RUN apk update && apk add --no-cache bash curl
COPY --from=builder /app/sensor_generator /app/sensor_generator
COPY wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Рабочая директория
WORKDIR /app

# Запуск генератора данных
CMD ["./wait-for-it.sh", "rabbitmq:5672", "--", "./sensor_generator"]