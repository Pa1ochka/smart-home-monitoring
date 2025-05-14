import pika
import json
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
import time

# Настройка базы данных
DATABASE_URL = "postgresql://postgres:admin12345@postgres:5432/smarthome"

# Объявляем Base ДО его использования
Base = declarative_base()


# Модель данных для показаний датчиков
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Функция для ожидания БД
def wait_for_db():
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Успешное подключение к PostgreSQL")
                return engine
        except Exception as e:
            attempt += 1
            print(f"Попытка {attempt}/{max_attempts}: Ошибка - {str(e)}")
            time.sleep(5)
    raise Exception(f"Не удалось подключиться к PostgreSQL "
                    f"после {max_attempts} попыток")


# Инициализация БД
engine = wait_for_db()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    if (temperature < TEMP_THRESHOLD["min"] or
            temperature > TEMP_THRESHOLD["max"]):
        notification = f"Температура вне диапазона: {temperature}°C"
    elif (humidity < HUMIDITY_THRESHOLD["min"] or
          humidity > HUMIDITY_THRESHOLD["max"]):
        notification = f"Влажность вне диапазона: {humidity}%"

    if notification:
        ch.queue_declare(queue='notifications', durable=True)
        ch.basic_publish(
            exchange='',
            routing_key='notifications',
            body=json.dumps({"message": notification}),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"Отправлено уведомление: {notification}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


# Подключение к RabbitMQ и запуск потребителя
def start_consuming():
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='sensor_data', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='sensor_data', on_message_callback=callback)
    print("Ожидание данных от сенсоров...")
    channel.start_consuming()


if __name__ == "__main__":
    start_consuming()
