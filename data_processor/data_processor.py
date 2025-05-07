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