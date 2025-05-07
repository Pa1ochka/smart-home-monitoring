package main

import (
    "encoding/json"
    "log"
    "math/rand"
    "time"

    "github.com/streadway/amqp"
)

type SensorData struct {
    Temperature float64 `json:"temperature"`
    Humidity    float64 `json:"humidity"`
}

func main() {
    // Подключение к RabbitMQ
    conn, err := amqp.Dial("amqp://guest:guest@localhost:5672/")
    if err != nil {
        log.Fatalf("Failed to connect to RabbitMQ: %v", err)
    }
    defer conn.Close()

    ch, err := conn.Channel()
    if err != nil {
        log.Fatalf("Failed to open a channel: %v", err)
    }
    defer ch.Close()

    // Объявление очереди
    q, err := ch.QueueDeclare(
        "sensor_data", // Имя очереди
        true,          // Durable
        false,         // Delete when unused
        false,         // Exclusive
        false,         // No-wait
        nil,           // Arguments
    )
    if err != nil {
        log.Fatalf("Failed to declare a queue: %v", err)
    }

    // Инициализация генератора случайных чисел
    rand.Seed(time.Now().UnixNano())

    // Генерация и отправка данных
    for {
        data := SensorData{
            Temperature: 15.0 + rand.Float64()*15.0, // 15.0–30.0°C
            Humidity:    20.0 + rand.Float64()*60.0, // 20.0–80.0%
        }

        body, err := json.Marshal(data)
        if err != nil {
            log.Printf("Failed to marshal JSON: %v", err)
            continue
        }

        err = ch.Publish(
            "",     // Exchange
            q.Name, // Routing key
            false,  // Mandatory
            false,  // Immediate
            amqp.Publishing{
                ContentType:  "application/json",
                Body:         body,
                DeliveryMode: amqp.Persistent,
            })
        if err != nil {
            log.Printf("Failed to publish message: %v", err)
        } else {
            log.Printf("Sent: %+v", data)
        }

        // Пауза 5 секунд
        time.Sleep(5 * time.Second)
    }
}