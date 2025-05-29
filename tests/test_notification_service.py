import unittest
from unittest.mock import Mock
import json
import logging
from io import StringIO

from notification_service.notification_service import process_notification

class TestNotification(unittest.TestCase):
    def setUp(self):
        """
        Инициализирует моки и захват логов для тестов уведомлений.
        """
        self.channel = Mock()
        self.method = Mock()
        self.properties = Mock()
        self.log_output = StringIO()
        # Настройка логгера для модуля уведомлений
        logger = logging.getLogger('notification_service')
        logger.handlers = [logging.StreamHandler(self.log_output)]
        logger.setLevel(logging.INFO)

    def test_valid_notification(self):
        """
        Тестирует логирование корректного уведомления из очереди.
        """
        alert_message = {"message": "Температура вне диапазона: 30.0°C"}
        body = json.dumps(alert_message).encode()

        process_notification(self.channel, self.method, self.properties, body)

        # Проверка содержимого логов
        log_content = self.log_output.getvalue()
        self.assertIn("Получено уведомление: Температура вне диапазона: 30.0°C", log_content)

    def test_invalid_json(self):
        """
        Тестирует обработку некорректного JSON-сообщения.
        """
        body = b"invalid json"

        process_notification(self.channel, self.method, self.properties, body)

        # Проверка логов на наличие ошибки
        log_content = self.log_output.getvalue()
        self.assertIn("Ошибка при разборе JSON", log_content)

if __name__ == '__main__':
    unittest.main()