from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, DateTime
import redis
from datetime import datetime, timezone
from typing import List
import json

# Настройка FastAPI
app = FastAPI(title="Smart Home Monitoring API")

# Настройка базы данных
DATABASE_URL = "postgresql://postgres:admin12345@postgres:5432/smarthome"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель данных для сенсоров (та же, что в data_processor)
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Настройка Redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Модель для ответа API
from pydantic import BaseModel
class SensorDataResponse(BaseModel):
    id: int
    temperature: float
    humidity: float
    timestamp: datetime

# Эндпоинт для получения последних данных (с кэшированием в Redis)
@app.get("/latest", response_model=SensorDataResponse)
async def get_latest_data():
    # Проверка кэша
    cached_data = redis_client.get("latest_sensor_data")
    if cached_data:
        return json.loads(cached_data)

    # Получение данных из базы
    db = SessionLocal()
    latest_data = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
    db.close()

    if latest_data:
        # Сохранение в кэш
        redis_client.setex("latest_sensor_data", 60, json.dumps({
            "id": latest_data.id,
            "temperature": latest_data.temperature,
            "humidity": latest_data.humidity,
            "timestamp": latest_data.timestamp.isoformat()
        }))
        return latest_data
    return {"message": "No data available"}

# Эндпоинт для получения истории данных
@app.get("/history", response_model=List[SensorDataResponse])
async def get_history(limit: int = 10):
    db = SessionLocal()
    data = db.query(SensorData).order_by(SensorData.timestamp.desc()).limit(limit).all()
    db.close()
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)