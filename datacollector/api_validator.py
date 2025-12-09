"""
Валидатор ответов API маркетплейсов.
Проверяет формат ответов и уведомляет при изменениях.
"""
import logging
from typing import Optional, Tuple, List
from pydantic import ValidationError

from datacollector.api_schemas import (
    OzonFBSListResponse,
    OzonFBOListResponse,
    OzonFinanceResponse,
    OzonSupplyOrderListResponse,
    OzonSupplyOrderGetResponse,
    OzonBundleResponse,
    OzonReportCreateResponse,
    OzonReportInfoResponse,
)
from datacollector.notifier import APIValidationNotifier

logger = logging.getLogger(__name__)


class APIValidator:
    """Валидатор ответов API"""

    @staticmethod
    def _get_extra_fields(data: dict, model_fields: set) -> List[str]:
        """Получить список новых полей, которых нет в модели"""
        if not isinstance(data, dict):
            return []
        data_fields = set(data.keys())
        return list(data_fields - model_fields)

    @staticmethod
    def validate_ozon_fbs_list(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v3/posting/fbs/list"""
        api_name = "FBS Orders (/v3/posting/fbs/list)"
        try:
            validated = OzonFBSListResponse(**response_data)

            # Проверяем новые поля
            extra = APIValidator._get_extra_fields(response_data, set(OzonFBSListResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon FBS API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_fbo_list(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v2/posting/fbo/list"""
        api_name = "FBO Orders (/v2/posting/fbo/list)"
        try:
            validated = OzonFBOListResponse(**response_data)

            extra = APIValidator._get_extra_fields(response_data, set(OzonFBOListResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon FBO API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_finance(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v3/finance/transaction/list"""
        api_name = "Finance (/v3/finance/transaction/list)"
        try:
            validated = OzonFinanceResponse(**response_data)

            extra = APIValidator._get_extra_fields(response_data, set(OzonFinanceResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Finance API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_supply_list(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v3/supply-order/list"""
        api_name = "Supply Orders (/v3/supply-order/list)"
        try:
            validated = OzonSupplyOrderListResponse(**response_data)

            extra = APIValidator._get_extra_fields(response_data, set(OzonSupplyOrderListResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Supply List API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_supply_get(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v3/supply-order/get"""
        api_name = "Supply Orders Get (/v3/supply-order/get)"
        try:
            validated = OzonSupplyOrderGetResponse(**response_data)

            extra = APIValidator._get_extra_fields(response_data, set(OzonSupplyOrderGetResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Supply Get API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_bundle(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v1/supply-order/bundle"""
        api_name = "Supply Bundle (/v1/supply-order/bundle)"
        try:
            validated = OzonBundleResponse(**response_data)

            extra = APIValidator._get_extra_fields(response_data, set(OzonBundleResponse.model_fields.keys()))
            if extra:
                APIValidationNotifier.notify_new_fields("Ozon", api_name, extra)

            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Bundle API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_report_create(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v1/report/products/create"""
        api_name = "Report Create (/v1/report/products/create)"
        try:
            validated = OzonReportCreateResponse(**response_data)
            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Report Create API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg

    @staticmethod
    def validate_ozon_report_info(response_data: dict) -> Tuple[bool, Optional[str]]:
        """Валидация ответа /v1/report/info"""
        api_name = "Report Info (/v1/report/info)"
        try:
            validated = OzonReportInfoResponse(**response_data)
            return True, None
        except ValidationError as e:
            error_msg = str(e)
            logger.error(f"Ozon Report Info API validation error: {error_msg}")
            APIValidationNotifier.notify_validation_error("Ozon", api_name, error_msg)
            return False, error_msg
