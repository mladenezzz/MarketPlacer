"""
Модуль уведомлений для datacollector.
Отправляет сообщения в Telegram при ошибках валидации API.
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Отправка уведомлений в Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Отправить сообщение в Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False


class APIValidationNotifier:
    """Уведомления об изменениях в API маркетплейсов"""

    _instance: Optional['APIValidationNotifier'] = None
    _notifier: Optional[TelegramNotifier] = None
    _notified_errors: set = set()  # Кэш уведомлений, чтобы не спамить

    @classmethod
    def initialize(cls, bot_token: str, chat_id: str):
        """Инициализация уведомителя"""
        cls._notifier = TelegramNotifier(bot_token, chat_id)
        cls._notified_errors = set()

    @classmethod
    def notify_validation_error(cls, marketplace: str, api_name: str, error: str):
        """Уведомить об ошибке валидации API"""
        if cls._notifier is None:
            logger.warning("TelegramNotifier not initialized, skipping notification")
            return

        # Формируем ключ для дедупликации
        error_key = f"{marketplace}:{api_name}:{error[:100]}"

        # Не отправляем повторно одну и ту же ошибку
        if error_key in cls._notified_errors:
            return

        message = (
            f"<b>API Schema Error</b>\n\n"
            f"<b>Marketplace:</b> {marketplace}\n"
            f"<b>API:</b> {api_name}\n"
            f"<b>Error:</b>\n<code>{error[:500]}</code>\n\n"
            f"<i>Требуется обновление datacollector!</i>"
        )

        if cls._notifier.send_message(message):
            cls._notified_errors.add(error_key)
            logger.info(f"Sent validation error notification for {marketplace}/{api_name}")

    @classmethod
    def notify_new_fields(cls, marketplace: str, api_name: str, new_fields: list):
        """Уведомить о новых полях в API"""
        if cls._notifier is None:
            return

        if not new_fields:
            return

        # Формируем ключ для дедупликации
        fields_str = ",".join(sorted(new_fields))
        error_key = f"{marketplace}:{api_name}:fields:{fields_str}"

        if error_key in cls._notified_errors:
            return

        message = (
            f"<b>API New Fields Detected</b>\n\n"
            f"<b>Marketplace:</b> {marketplace}\n"
            f"<b>API:</b> {api_name}\n"
            f"<b>New fields:</b>\n<code>{', '.join(new_fields)}</code>\n\n"
            f"<i>Возможно, API был обновлён. Проверьте документацию.</i>"
        )

        if cls._notifier.send_message(message):
            cls._notified_errors.add(error_key)
            logger.info(f"Sent new fields notification for {marketplace}/{api_name}")

    @classmethod
    def clear_cache(cls):
        """Очистить кэш уведомлений (для тестов или периодической очистки)"""
        cls._notified_errors = set()
