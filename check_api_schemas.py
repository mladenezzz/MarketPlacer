#!/usr/bin/env python3
"""
Скрипт для проверки актуальности API маркетплейсов.
Делает тестовые запросы к API и валидирует формат ответов.

Запуск:
    python check_api_schemas.py [--ozon] [--wb] [--verbose]

Примеры:
    python check_api_schemas.py           # Проверить все API
    python check_api_schemas.py --ozon    # Только Ozon
    python check_api_schemas.py --wb      # Только Wildberries
    python check_api_schemas.py -v        # Подробный вывод
"""

import sys
import os
import argparse
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импортируем модели и схемы валидации
from app.models import Token
from datacollector.api_schemas import (
    validate_ozon_fbs_list,
    validate_ozon_fbo_list,
    validate_ozon_finance,
    validate_ozon_supply_list,
    validate_ozon_supply_get,
    validate_ozon_bundle,
    validate_wb_incomes,
    validate_wb_sales,
    validate_wb_orders,
    validate_wb_stocks,
    validate_wb_cards,
)


class APIChecker:
    """Проверка API маркетплейсов"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []

        # Подключение к БД для получения токенов
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def log(self, message: str, level: str = "INFO"):
        """Вывод сообщения"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "[INFO]",
            "OK": "[ OK ]",
            "WARN": "[WARN]",
            "ERROR": "[FAIL]",
        }.get(level, "")
        print(f"[{timestamp}] {prefix} {message}")

    def add_result(self, api_name: str, success: bool, message: str, extra_fields: list = None):
        """Добавить результат проверки"""
        self.results.append({
            "api": api_name,
            "success": success,
            "message": message,
            "extra_fields": extra_fields or []
        })

    # =========================================================================
    # OZON API
    # =========================================================================

    def check_ozon(self):
        """Проверка всех Ozon API"""
        self.log("=" * 50)
        self.log("Проверка Ozon API")
        self.log("=" * 50)

        # Получаем первый активный Ozon токен
        token = self.session.query(Token).filter_by(
            marketplace='ozon',
            is_active=True
        ).first()

        if not token:
            self.log("Нет активных Ozon токенов", "ERROR")
            return

        headers = {
            'Client-Id': str(token.client_id),
            'Api-Key': token.token,
            'Content-Type': 'application/json'
        }
        base_url = 'https://api-seller.ozon.ru'

        self.log(f"Используется токен: {token.name or token.id}")

        # Проверяем каждый endpoint
        self._check_ozon_fbs_list(base_url, headers)
        time.sleep(1)
        self._check_ozon_fbo_list(base_url, headers)
        time.sleep(1)
        self._check_ozon_finance(base_url, headers)
        time.sleep(1)
        self._check_ozon_supply_list(base_url, headers)

    def _check_ozon_fbs_list(self, base_url: str, headers: dict):
        """Проверка /v3/posting/fbs/list"""
        api_name = "Ozon FBS Orders (/v3/posting/fbs/list)"
        self.log(f"Проверка {api_name}...")

        try:
            url = f"{base_url}/v3/posting/fbs/list"
            payload = {
                "dir": "ASC",
                "filter": {
                    "since": (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "to": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "status": ""
                },
                "limit": 10,
                "offset": 0,
                "with": {
                    "analytics_data": True,
                    "financial_data": True
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                self.add_result(api_name, False, f"HTTP {response.status_code}")
                return

            data = response.json()
            success, message, extra = validate_ozon_fbs_list(data)

            if success:
                postings_count = len(data.get('result', {}).get('postings', []))
                self.log(f"{api_name}: OK ({postings_count} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")

            self.add_result(api_name, success, message, extra)

        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    def _check_ozon_fbo_list(self, base_url: str, headers: dict):
        """Проверка /v2/posting/fbo/list"""
        api_name = "Ozon FBO Orders (/v2/posting/fbo/list)"
        self.log(f"Проверка {api_name}...")

        try:
            url = f"{base_url}/v2/posting/fbo/list"
            payload = {
                "dir": "ASC",
                "filter": {
                    "since": (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "to": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "status": ""
                },
                "limit": 10,
                "offset": 0,
                "with": {
                    "analytics_data": True,
                    "financial_data": True
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                self.add_result(api_name, False, f"HTTP {response.status_code}")
                return

            data = response.json()
            success, message, extra = validate_ozon_fbo_list(data)

            if success:
                postings_count = len(data.get('result', []))
                self.log(f"{api_name}: OK ({postings_count} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")

            self.add_result(api_name, success, message, extra)

        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    def _check_ozon_finance(self, base_url: str, headers: dict):
        """Проверка /v3/finance/transaction/list"""
        api_name = "Ozon Finance (/v3/finance/transaction/list)"
        self.log(f"Проверка {api_name}...")

        try:
            url = f"{base_url}/v3/finance/transaction/list"
            today = datetime.now(timezone.utc)
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            payload = {
                "filter": {
                    "date": {
                        "from": month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                        "to": today.strftime('%Y-%m-%dT%H:%M:%S.999Z')
                    },
                    "operation_type": [],
                    "posting_number": "",
                    "transaction_type": "all"
                },
                "page": 1,
                "page_size": 10
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                self.add_result(api_name, False, f"HTTP {response.status_code}")
                return

            data = response.json()
            success, message, extra = validate_ozon_finance(data)

            if success:
                ops_count = len(data.get('result', {}).get('operations', []))
                self.log(f"{api_name}: OK ({ops_count} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")

            self.add_result(api_name, success, message, extra)

        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    def _check_ozon_supply_list(self, base_url: str, headers: dict):
        """Проверка /v3/supply-order/list"""
        api_name = "Ozon Supply Orders (/v3/supply-order/list)"
        self.log(f"Проверка {api_name}...")

        try:
            url = f"{base_url}/v3/supply-order/list"
            payload = {
                "filter": {
                    "states": ["COMPLETED"]
                },
                "limit": 10,
                "sort_by": 1
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                self.add_result(api_name, False, f"HTTP {response.status_code}")
                return

            data = response.json()
            success, message, extra = validate_ozon_supply_list(data)

            if success:
                orders_count = len(data.get('order_ids', []))
                self.log(f"{api_name}: OK ({orders_count} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")

            self.add_result(api_name, success, message, extra)

        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    # =========================================================================
    # Wildberries API
    # =========================================================================

    def check_wb(self):
        """Проверка всех WB API"""
        self.log("=" * 50)
        self.log("Проверка Wildberries API")
        self.log("=" * 50)

        # Получаем первый активный WB токен
        token = self.session.query(Token).filter_by(
            marketplace='wildberries',
            is_active=True
        ).first()

        if not token:
            self.log("Нет активных WB токенов", "ERROR")
            return

        self.log(f"Используется токен: {token.name or token.id}")

        # Проверяем каждый endpoint
        self._check_wb_statistics(token.token)
        time.sleep(60)  # WB требует 60 сек между запросами
        self._check_wb_cards(token.token)

    def _check_wb_statistics(self, api_key: str):
        """Проверка Statistics API (incomes, sales, orders, stocks)"""
        from wb_api import WBApi

        api = WBApi(api_key)
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Incomes
        api_name = "WB Statistics: Incomes"
        self.log(f"Проверка {api_name}...")
        try:
            data = api.statistics.get_data(endpoint="incomes", date_from=date_from, flag=0)
            if data is None:
                data = []
            success, message, extra = validate_wb_incomes(data)
            if success:
                self.log(f"{api_name}: OK ({len(data)} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")
            self.add_result(api_name, success, message, extra)
        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

        time.sleep(60)

        # Sales
        api_name = "WB Statistics: Sales"
        self.log(f"Проверка {api_name}...")
        try:
            data = api.statistics.get_data(endpoint="sales", date_from=date_from, flag=0)
            if data is None:
                data = []
            success, message, extra = validate_wb_sales(data)
            if success:
                self.log(f"{api_name}: OK ({len(data)} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")
            self.add_result(api_name, success, message, extra)
        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

        time.sleep(60)

        # Orders
        api_name = "WB Statistics: Orders"
        self.log(f"Проверка {api_name}...")
        try:
            data = api.statistics.get_data(endpoint="orders", date_from=date_from, flag=0)
            if data is None:
                data = []
            success, message, extra = validate_wb_orders(data)
            if success:
                self.log(f"{api_name}: OK ({len(data)} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")
            self.add_result(api_name, success, message, extra)
        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

        time.sleep(60)

        # Stocks
        api_name = "WB Statistics: Stocks"
        self.log(f"Проверка {api_name}...")
        try:
            stocks_data = api.statistics.get_stocks(date_from=date_from)
            # Конвертируем объекты в dict
            data = [{"barcode": s.barcode, "warehouseName": s.warehouse_name,
                    "quantity": s.quantity, "quantityFull": s.quantity_full,
                    "inWayToClient": s.in_way_to_client, "inWayFromClient": s.in_way_from_client,
                    "nmId": s.nm_id, "supplierArticle": s.supplier_article} for s in stocks_data]
            success, message, extra = validate_wb_stocks(data)
            if success:
                self.log(f"{api_name}: OK ({len(data)} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")
            self.add_result(api_name, success, message, extra)
        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    def _check_wb_cards(self, api_key: str):
        """Проверка Content API (cards)"""
        api_name = "WB Content: Cards (/content/v2/get/cards/list)"
        self.log(f"Проверка {api_name}...")

        try:
            url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
            headers = {
                "Authorization": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "settings": {
                    "cursor": {"limit": 10},
                    "filter": {"withPhoto": -1}
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.log(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                self.add_result(api_name, False, f"HTTP {response.status_code}")
                return

            data = response.json()
            success, message, extra = validate_wb_cards(data)

            if success:
                cards_count = len(data.get('cards', []))
                self.log(f"{api_name}: OK ({cards_count} записей)", "OK")
                if extra and self.verbose:
                    self.log(f"  Новые поля: {extra}", "WARN")
            else:
                self.log(f"{api_name}: {message}", "ERROR")

            self.add_result(api_name, success, message, extra)

        except Exception as e:
            self.log(f"{api_name}: {str(e)}", "ERROR")
            self.add_result(api_name, False, str(e))

    # =========================================================================
    # Summary
    # =========================================================================

    def print_summary(self):
        """Вывод итогов проверки"""
        self.log("=" * 50)
        self.log("ИТОГИ ПРОВЕРКИ")
        self.log("=" * 50)

        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total - passed

        for result in self.results:
            status = "[ OK ]" if result['success'] else "[FAIL]"
            extra_info = ""
            if result['extra_fields']:
                extra_info = f" (новые поля: {len(result['extra_fields'])})"
            print(f"  {status} {result['api']}: {result['message']}{extra_info}")

        self.log("-" * 50)
        self.log(f"Всего проверено: {total}")
        self.log(f"Успешно: {passed}", "OK" if passed == total else "INFO")
        if failed > 0:
            self.log(f"Ошибок: {failed}", "ERROR")

        # Выводим все новые поля
        all_extra = []
        for r in self.results:
            if r['extra_fields']:
                all_extra.extend([(r['api'], f) for f in r['extra_fields']])

        if all_extra:
            self.log("-" * 50)
            self.log("Обнаружены новые поля в API:", "WARN")
            for api, field in all_extra:
                print(f"    {api}: {field}")

        return failed == 0

    def close(self):
        """Закрытие соединений"""
        self.session.close()


def main():
    parser = argparse.ArgumentParser(description='Проверка API маркетплейсов')
    parser.add_argument('--ozon', action='store_true', help='Проверить только Ozon')
    parser.add_argument('--wb', action='store_true', help='Проверить только Wildberries')
    parser.add_argument('-v', '--verbose', action='store_true', help='Подробный вывод')
    args = parser.parse_args()

    checker = APIChecker(verbose=args.verbose)

    try:
        # Если не указаны флаги - проверяем все
        check_all = not args.ozon and not args.wb

        if check_all or args.ozon:
            checker.check_ozon()

        if check_all or args.wb:
            checker.check_wb()

        success = checker.print_summary()
        sys.exit(0 if success else 1)

    finally:
        checker.close()


if __name__ == '__main__':
    main()
