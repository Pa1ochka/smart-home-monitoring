import pika
import json
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
import time
import logging
import redis

# Логирование для отслеживания работы с данными сенсоров
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
sensor_logger = logging.getLogger(__name__)

# Подключение к PostgreSQL для хранения данных
DATABASE_URL = "postgresql://postgres:admin12345@postgres:5432/smarthome"
Base = declarative_base()

# Модель для хранения показаний сенсоров
class SensorReading(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def wait_for_database_connection():
    """
    Проверяет доступность PostgreSQL с повторными попытками при сбоях.
    """
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_timeout=30)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                sensor_logger.info("Подключение к PostgreSQL установлено")
                return engine
        except Exception as e:
            attempt += 1
            sensor_logger.warning(f"Попытка {attempt}/{max_attempts}: Не удалось подключиться - {str(e)}")
            time.sleep(5)
    raise Exception(f"Не удалось подключиться к PostgreSQL после {max_attempts} попыток")

def init_database():
    """
    Создает таблицы и возвращает настроенное соединение с базой данных.
    """
    engine = wait_for_database_connection()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal

# Пороговые значения для температуры и влажности
TEMP_THRESHOLD = {"min": 16.0, "max": 29.0}
HUMIDITY_THRESHOLD = {"min": 25.0, "max": 75.0}

# Клиент для кэширования последних данных
cache_client = redis.Redis(host='redis', port=6379, decode_responses=True)

def process_sensor_data(channel, method, properties, body, session_local):
    """
    Сохраняет данные сенсоров в базу, кэширует их и отправляет уведомления при выходе за пороги.
    """
    try:
        sensor_reading = json.loads(body)
        temperature = sensor_reading["temperature"]
        humidity = sensor_reading["humidity"]
        sensor_logger.info(f"Получены данные: температура={temperature}°C, влажность={humidity}%")

        # Сохранение в базу данных
        with session_local() as db:
            reading = SensorReading(temperature=temperature, humidity=humidity)
            db.add(reading)
            db.commit()
            reading_id = reading.id

        # Кэширование в Redis
        cache_client.setex("latest_sensor_reading", 60, json.dumps({
            "id": reading_id,
            "temperature": temperature,
            "humidity": humidity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))

        # Проверка порогов и отправка уведомлений
        alert_message = None
        if temperature < TEMP_THRESHOLD["min"] or temperature > TEMP_THRESHOLD["max"]:
            alert_message = f"Температура вне диапазона: {temperature}°C"
        elif humidity < HUMIDITY_THRESHOLD["min"] or humidity > HUMIDITY_THRESHOLD["max"]:
            alert_message = f"Влажность вне диапазона: {humidity}%"

        if alert_message:
            channel.queue_declare(queue='notifications', durable=True)
            channel.basic_publish(
                exchange='',
                routing_key='notifications',
                body=json.dumps({"message": alert_message}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            sensor_logger.info(f"Отправлено уведомление: {alert_message}")

        channel.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        sensor_logger.error(f"Ошибка разбора JSON: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        sensor_logger.error(f"Ошибка обработки данных: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

def start_sensor_data_service():
    """
    Инициализирует подключение к RabbitMQ и начинает обработку данных из очереди сенсоров.
    """
    try:
        engine, SessionLocal = init_database()
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='sensor_data', durable=True)
        channel.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            process_sensor_data(ch, method, properties, body, SessionLocal)

        channel.basic_consume(queue='sensor_data', on_message_callback=callback)
        sensor_logger.info("Запуск ожидания данных сенсоров")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as e:
        sensor_logger.error(f"Не удалось подключиться к RabbitMQ: {e}")
        raise
    except Exception as e:
        sensor_logger.error(f"Ошибка запуска сервиса: {e}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    start_sensor_data_service()