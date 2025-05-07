import pika
import json
from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Настройка базы данных
DATABASE_URL = "postgresql://postgres:admin12345@localhost:5432/smarthome"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель данных для показаний датчиков
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Пороговые значения
TEMP_THRESHOLD = {"min": 18.0, "max": 28.0}
HUMIDITY_THRESHOLD = {"min": 30.0, "max": 70.0}

# Callback-функция для обработки сообщений из RabbitMQ
def callback(ch, method, properties, body):
    data = json.loads(body)
    temperature = data["temperature"]
    humidity = data["humidity"]
    print(f"Получены данные: температура={temperature}, влажность={humidity}")

    # Сохранение в базу данных
    db = SessionLocal()
    sensor_reading = SensorData(temperature=temperature, humidity=humidity)
    db.add(sensor_reading)
    db.commit()
    db.close()

    # Проверка пороговых значений
    notification = None
    if temperature < TEMP_THRESHOLD["min"] or temperature > TEMP_THRESHOLD["max"]:
        notification = f"Температура вне диапазона: {temperature}°C"
    elif humidity < HUMIDITY_THRESHOLD["min"] or humidity > HUMIDITY_THRESHOLD["max"]:
        notification = f"Влажность вне диапазона: {humidity}%"

    if notification:
        # Отправка уведомления в очередь
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='notifications', durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='notifications',
            body=json.dumps({"message": notification}),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"Отправлено уведомление: {notification}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

# Подключение к RabbitMQ и запуск потребителя
def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='sensor_data', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='sensor_data', on_message_callback=callback)
    print("Ожидание данных от сенсоров...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()