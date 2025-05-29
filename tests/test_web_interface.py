from fastapi.testclient import TestClient
import unittest
from unittest.mock import MagicMock, patch
from web_interface.web_interface import app, SensorReading
import json
from datetime import datetime, timezone

client = TestClient(app)

class TestWebInterface(unittest.TestCase):
    @patch('web_interface.web_interface.cache_client')
    @patch('web_interface.web_interface.SessionLocal')
    def test_get_latest_from_redis(self, mock_db_session, mock_redis):
        """
        Тестирует возврат последних данных сенсоров из кэша Redis.
        """
        mock_redis.get.return_value = json.dumps({
            "id": 1,
            "temperature": 20.0,
            "humidity": 50.0,
            "timestamp": "2025-05-29T10:00:00Z"
        })

        response = client.get("/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["temperature"], 20.0)
        mock_db_session.assert_not_called()

    @patch('web_interface.web_interface.cache_client')
    @patch('web_interface.web_interface.SessionLocal')
    def test_get_latest_from_postgres(self, mock_db_session, mock_redis):
        """
        Тестирует получение данных из PostgreSQL при отсутствии кэша в Redis.
        """
        mock_redis.get.return_value = None
        mock_db = MagicMock()
        mock_db_session().__enter__.return_value = mock_db
        mock_reading = SensorReading(
            id=1,
            temperature=22.0,
            humidity=55.0,
            timestamp=datetime(2025, 5, 29, 10, 0, tzinfo=timezone.utc)
        )
        mock_db.query().order_by().first.return_value = mock_reading

        response = client.get("/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["temperature"], 22.0)
        mock_redis.setex.assert_called_once()

    @patch('web_interface.web_interface.SessionLocal')
    def test_get_history(self, mock_db_session):
        """
        Тестирует получение истории показаний сенсоров из базы данных.
        """
        mock_db = MagicMock()
        mock_db_session().__enter__.return_value = mock_db
        mock_readings = [
            SensorReading(
                id=i,
                temperature=20.0 + i,
                humidity=50.0 + i,
                timestamp=datetime(2025, 5, 29, 10, i, tzinfo=timezone.utc)
            ) for i in range(3)
        ]
        mock_db.query().order_by().limit().all.return_value = mock_readings

        response = client.get("/history?limit=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)
        self.assertEqual(response.json()[0]["temperature"], 20.0)

    def test_health_check(self):
        """
        Тестирует эндпоинт проверки состояния сервиса.
        """
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

if __name__ == '__main__':
    unittest.main()