import sys
import os
import unittest
import json
from data_processor.data_processor import callback
from unittest.mock import Mock

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestDataProcessor(unittest.TestCase):
    def test_threshold_check_temperature(self):
        # Тест для превышения температуры
        data = {"temperature": 30.0, "humidity": 50.0}
        body = json.dumps(data).encode()
        ch = Mock()
        method = Mock()
        properties = Mock()

        callback(ch, method, properties, body)
        # Проверяем, что уведомление отправлено
        ch.basic_publish.assert_called_once()
        # Проверяем содержимое уведомления
        call_args = ch.basic_publish.call_args
        self.assertEqual(call_args[1]['routing_key'], 'notifications')
        notification = json.loads(call_args[1]['body'])
        self.assertEqual(notification['message'],
                         "Температура вне диапазона: 30.0°C")
        ch.basic_ack.assert_called_with(delivery_tag=method.delivery_tag)

    def test_threshold_check_humidity(self):
        # Тест для низкой влажности
        data = {"temperature": 22.0, "humidity": 20.0}
        body = json.dumps(data).encode()
        ch = Mock()
        method = Mock()
        properties = Mock()

        callback(ch, method, properties, body)
        # Проверяем, что уведомление отправлено
        ch.basic_publish.assert_called_once()
        # Проверяем содержимое уведомления
        call_args = ch.basic_publish.call_args
        self.assertEqual(call_args[1]['routing_key'], 'notifications')
        notification = json.loads(call_args[1]['body'])
        self.assertEqual(notification['message'],
                         "Влажность вне диапазона: 20.0%")
        ch.basic_ack.assert_called_with(delivery_tag=method.delivery_tag)

    def test_normal_data(self):
        # Тест для нормальных данных
        data = {"temperature": 22.0, "humidity": 50.0}
        body = json.dumps(data).encode()
        ch = Mock()
        method = Mock()
        properties = Mock()

        callback(ch, method, properties, body)
        ch.basic_publish.assert_not_called()  # Уведомление не отправлено
        ch.basic_ack.assert_called_with(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    unittest.main()
