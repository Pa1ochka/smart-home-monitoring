import unittest
from unittest.mock import MagicMock, patch
import json

from sensor_data.sensor_data import process_sensor_data

class TestSensorData(unittest.TestCase):
    def setUp(self):
        """
        Инициализирует моки для тестов обработки данных сенсоров.
        """
        self.channel = MagicMock()
        self.method = MagicMock(delivery_tag=1)
        self.properties = MagicMock()
        self.mock_db_session = MagicMock()

    def test_high_temperature_alert(self):
        """
        Тестирует отправку уведомления при превышении порога температуры.
        """
        mock_db = MagicMock()
        self.mock_db_session().__enter__.return_value = mock_db
        mock_db.commit.return_value = None
        mock_reading = MagicMock(id=1)
        mock_db.add.return_value = mock_reading

        sensor_data = {"temperature": 30.0, "humidity": 50.0}
        body = json.dumps(sensor_data).encode()

        with patch('sensor_data.sensor_data.cache_client') as mock_redis:
            process_sensor_data(self.channel, self.method, self.properties, body, self.mock_db_session)

            # Проверка отправки уведомления
            self.channel.basic_publish.assert_called_once()
            call_args = self.channel.basic_publish.call_args
            self.assertEqual(call_args[1]['routing_key'], 'notifications')
            alert_message = json.loads(call_args[1]['body'])
            self.assertEqual(alert_message['message'], "Температура вне диапазона: 30.0°C")

            # Проверка кэширования в Redis
            mock_redis.setex.assert_called_once()
            redis_call = mock_redis.setex.call_args
            self.assertEqual(redis_call[0][0], "latest_sensor_reading")
            self.assertEqual(redis_call[0][1], 60)
            redis_data = json.loads(redis_call[0][2])
            self.assertEqual(redis_data["temperature"], 30.0)
            self.assertEqual(redis_data["humidity"], 50.0)

            # Проверка подтверждения сообщения
            self.channel.basic_ack.assert_called_with(delivery_tag=self.method.delivery_tag)

    def test_low_humidity_alert(self):
        """
        Тестирует отправку уведомления при низкой влажности.
        """
        mock_db = MagicMock()
        self.mock_db_session().__enter__.return_value = mock_db
        mock_db.commit.return_value = None
        mock_reading = MagicMock(id=1)
        mock_db.add.return_value = mock_reading

        sensor_data = {"temperature": 22.0, "humidity": 20.0}
        body = json.dumps(sensor_data).encode()

        with patch('sensor_data.sensor_data.cache_client') as mock_redis:
            process_sensor_data(self.channel, self.method, self.properties, body, self.mock_db_session)

            # Проверка отправки уведомления
            self.channel.basic_publish.assert_called_once()
            call_args = self.channel.basic_publish.call_args
            self.assertEqual(call_args[1]['routing_key'], 'notifications')
            alert_message = json.loads(call_args[1]['body'])
            self.assertEqual(alert_message['message'], "Влажность вне диапазона: 20.0%")

            # Проверка кэширования
            mock_redis.setex.assert_called_once()

            # Проверка подтверждения
            self.channel.basic_ack.assert_called_with(delivery_tag=self.method.delivery_tag)

    def test_normal_sensor_data(self):
        """
        Тестирует отсутствие уведомлений при нормальных значениях сенсоров.
        """
        mock_db = MagicMock()
        self.mock_db_session().__enter__.return_value = mock_db
        mock_db.commit.return_value = None
        mock_reading = MagicMock(id=1)
        mock_db.add.return_value = mock_reading

        sensor_data = {"temperature": 20.0, "humidity": 50.0}
        body = json.dumps(sensor_data).encode()

        with patch('sensor_data.sensor_data.cache_client') as mock_redis:
            process_sensor_data(self.channel, self.method, self.properties, body, self.mock_db_session)

            # Проверка отсутствия уведомлений
            self.channel.basic_publish.assert_not_called()

            # Проверка кэширования
            mock_redis.setex.assert_called_once()

            # Проверка подтверждения
            self.channel.basic_ack.assert_called_with(delivery_tag=self.method.delivery_tag)

    def test_invalid_json(self):
        """
        Тестирует обработку некорректного JSON в сообщениях.
        """
        body = b"invalid json"

        with patch('sensor_data.sensor_data.cache_client') as mock_redis:
            process_sensor_data(self.channel, self.method, self.properties, body, self.mock_db_session)

            # Проверка отсутствия уведомлений и кэширования
            self.channel.basic_publish.assert_not_called()
            mock_redis.setex.assert_not_called()
            self.mock_db_session.assert_not_called()

            # Проверка подтверждения
            self.channel.basic_ack.assert_called_with(delivery_tag=self.method.delivery_tag)

if __name__ == '__main__':
    unittest.main()