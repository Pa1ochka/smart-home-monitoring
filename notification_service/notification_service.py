import pika
import json
import logging

# Логирование для отслеживания работы сервиса уведомлений
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
notification_logger = logging.getLogger(__name__)

def start_notification_service():
    """
    Инициализирует подключение к RabbitMQ и начинает обработку сообщений из очереди уведомлений.
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='notifications', durable=True)
        # Ограничивает количество одновременно обрабатываемых сообщений для стабильности
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='notifications', on_message_callback=process_notification, auto_ack=True)
        notification_logger.info("Запуск ожидания сообщений из очереди уведомлений")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as e:
        notification_logger.error(f"Не удалось подключиться к RabbitMQ: {e}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

def process_notification(ch, method, properties, body):
    """
    Обрабатывает уведомления и выводит в консоль
    """
    try:
        alert_message = json.loads(body)
        notification_logger.info(f"Получено уведомление: {alert_message['message']}")
    except json.JSONDecodeError as e:
        notification_logger.error(f"Ошибка при разборе JSON-сообщения: {e}")

if __name__ == "__main__":
    start_notification_service()