package main

import (
    "encoding/json"
    "log"
    "math/rand"
    "time"

    "github.com/streadway/amqp"
)

// SensorData определяет формат данных сенсоров для отправки в RabbitMQ.
type SensorData struct {
    Temperature float64 `json:"temperature"`
    Humidity    float64 `json:"humidity"`
}

func main() {
    log.Println("Запуск генератора данных сенсоров...")

    // Установка соединения с RabbitMQ для отправки данных
    conn, err := amqp.Dial("amqp://guest:guest@rabbitmq:5672/")
    if err != nil {
        log.Fatalf("Не удалось подключиться к RabbitMQ: %v", err)
    }
    defer conn.Close()
    log.Println("Соединение с RabbitMQ установлено")

    channel, err := conn.Channel()
    if err != nil {
        log.Fatalf("Не удалось открыть канал: %v", err)
    }
    defer channel.Close()
    log.Println("Канал для сообщений открыт")

    // Настройка устойчивой очереди для данных сенсоров
    queue, err := channel.QueueDeclare(
        "sensor_data",
        true,  // Устойчивая очередь
        false, // Не удалять
        false, // Не эксклюзивная
        false, // Без ожидания
        nil,   // Без аргументов
    )
    if err != nil {
        log.Fatalf("Не удалось объявить очередь: %v", err)
    }
    log.Println("Очередь готова:", queue.Name)

    // Инициализация генератора случайных чисел для имитации данных
    rand.Seed(time.Now().UnixNano())

    // Генерация и отправка данных сенсоров с интервалом
    for {
        sensorData := SensorData{
            Temperature: 15.0 + rand.Float64()*15.0, // 15.0–30.0°C
            Humidity:    20.0 + rand.Float64()*60.0, // 20.0–80.0%
        }

        body, err := json.Marshal(sensorData)
        if err != nil {
            log.Printf("Ошибка сериализации данных: %v", err)
            time.Sleep(10 * time.Second)
            continue
        }

        err = channel.Publish(
            "",         // Обменник
            queue.Name, // Ключ маршрутизации
            false,      // Не обязательная доставка
            false,      // Не немедленная доставка
            amqp.Publishing{
                ContentType:  "application/json",
                Body:         body,
                DeliveryMode: amqp.Persistent,
            })
        if err != nil {
            log.Printf("Ошибка отправки данных: %v", err)
        } else {
            log.Printf("Отправлены данные: %+v", sensorData)
        }

        time.Sleep(10 * time.Second)
    }
}