import pika
import json

# Подключение к RabbitMQ и запуск потребителя
def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='notifications', durable=True)
    channel.basic_consume(queue='notifications', on_message_callback=callback, auto_ack=True)
    print("Ожидание уведомлений...")
    channel.start_consuming()

# Callback-функция для обработки уведомлений
def callback(ch, method, properties, body):
    notification = json.loads(body)
    print(f"[Уведомление] {notification['message']}")

if __name__ == "__main__":
    start_consuming()