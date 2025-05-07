import pika
import json

def callback(ch, method, properties, body):
    notification = json.loads(body)
    message = notification["message"]
    print(f"[Уведомление] {message}")
    # Здесь можно добавить отправку email, push-уведомлений и т.д.
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='notifications', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='notifications', on_message_callback=callback)
    print("Ожидание уведомлений...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()