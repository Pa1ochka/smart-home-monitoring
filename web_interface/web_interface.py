from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import redis
from datetime import datetime, timezone
from typing import List
import json
import uvicorn
from pydantic import BaseModel, ConfigDict


app = FastAPI(title="Smart Home Monitoring API")


DATABASE_URL = "postgresql://postgres:admin12345@postgres:5432/smarthome"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель для хранения данных сенсоров
class SensorReading(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Pydantic-модель для сериализации ответов API
class SensorReadingResponse(BaseModel):
    id: int
    temperature: float
    humidity: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# Клиент для кэширования последних данных
cache_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

@app.get("/health")
async def health_check():
    """
    Возвращает статус работоспособности сервиса.
    """
    return {"status": "healthy"}

@app.get("/latest", response_model=SensorReadingResponse)
async def get_latest_sensor_reading():
    """
    Извлекает последние данные сенсоров из кэша или базы данных.
    """
    try:
        # Попытка получения данных из кэша
        cached_reading = cache_client.get("latest_sensor_reading")
        if cached_reading:
            return SensorReadingResponse(**json.loads(cached_reading))

        # Запрос к базе данных при отсутствии кэша
        with SessionLocal() as db:
            latest = db.query(SensorReading).order_by(SensorReading.timestamp.desc()).first()
            if latest:
                response = SensorReadingResponse(
                    id=latest.id,
                    temperature=latest.temperature,
                    humidity=latest.humidity,
                    timestamp=latest.timestamp
                )
                # Сохранение данных в кэш
                redis_data = response.model_dump()
                redis_data["timestamp"] = redis_data["timestamp"].isoformat()
                cache_client.setex("latest_sensor_reading", 60, json.dumps(redis_data))
                return response
            raise HTTPException(status_code=404, detail="Данные сенсоров отсутствуют")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.get("/history", response_model=List[SensorReadingResponse])
async def get_sensor_history(limit: int = 10):
    """
    Возвращает последние записи из истории данных сенсоров.
    """
    try:
        with SessionLocal() as db:
            readings = db.query(SensorReading).order_by(SensorReading.timestamp.desc()).limit(limit).all()
            return [
                SensorReadingResponse(
                    id=r.id,
                    temperature=r.temperature,
                    humidity=r.humidity,
                    timestamp=r.timestamp
                ) for r in readings
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)