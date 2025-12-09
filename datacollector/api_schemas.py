"""
Pydantic-модели для валидации ответов API маркетплейсов.
Используются для проверки, что формат ответа API не изменился.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


# ==============================================================================
# OZON API Schemas
# ==============================================================================

# --- FBS Orders (/v3/posting/fbs/list) ---

class OzonFBSProduct(BaseModel):
    """Товар в FBS заказе"""
    model_config = ConfigDict(extra='allow')  # Разрешаем дополнительные поля

    sku: int
    offer_id: str
    name: Optional[str] = None
    quantity: int
    price: str
    barcode: Optional[str] = None


class OzonFBSFinancialData(BaseModel):
    """Финансовые данные FBS заказа"""
    model_config = ConfigDict(extra='allow')

    commission_amount: Optional[float] = None
    commission_percent: Optional[float] = None
    payout: Optional[float] = None


class OzonFBSPosting(BaseModel):
    """FBS отправление"""
    model_config = ConfigDict(extra='allow')

    posting_number: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    status: str
    in_process_at: Optional[str] = None
    shipment_date: Optional[str] = None
    products: List[OzonFBSProduct]
    financial_data: Optional[OzonFBSFinancialData] = None


class OzonFBSListResult(BaseModel):
    """Результат запроса FBS списка"""
    model_config = ConfigDict(extra='allow')

    postings: List[OzonFBSPosting]
    has_next: Optional[bool] = None


class OzonFBSListResponse(BaseModel):
    """Ответ /v3/posting/fbs/list"""
    model_config = ConfigDict(extra='allow')

    result: OzonFBSListResult


# --- FBO Orders (/v2/posting/fbo/list) ---

class OzonFBOProduct(BaseModel):
    """Товар в FBO заказе"""
    model_config = ConfigDict(extra='allow')

    sku: int
    offer_id: str
    name: Optional[str] = None
    quantity: int
    price: str


class OzonFBOPosting(BaseModel):
    """FBO отправление"""
    model_config = ConfigDict(extra='allow')

    posting_number: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    status: str
    in_process_at: Optional[str] = None
    shipment_date: Optional[str] = None
    products: List[OzonFBOProduct]
    financial_data: Optional[OzonFBSFinancialData] = None


class OzonFBOListResponse(BaseModel):
    """Ответ /v2/posting/fbo/list"""
    model_config = ConfigDict(extra='allow')

    result: List[OzonFBOPosting]


# --- Finance Transactions (/v3/finance/transaction/list) ---

class OzonFinancePosting(BaseModel):
    """Информация об отправлении в транзакции"""
    model_config = ConfigDict(extra='allow')

    posting_number: Optional[str] = None
    delivery_schema: Optional[str] = None


class OzonFinanceItem(BaseModel):
    """Товар в транзакции"""
    model_config = ConfigDict(extra='allow')

    sku: Optional[int] = None
    name: Optional[str] = None


class OzonFinanceOperation(BaseModel):
    """Финансовая операция"""
    model_config = ConfigDict(extra='allow')

    operation_id: int
    operation_type: str
    operation_date: str
    amount: Optional[float] = None
    accruals_for_sale: Optional[float] = None
    posting: Optional[OzonFinancePosting] = None
    items: Optional[List[OzonFinanceItem]] = None


class OzonFinanceResult(BaseModel):
    """Результат запроса транзакций"""
    model_config = ConfigDict(extra='allow')

    operations: List[OzonFinanceOperation]


class OzonFinanceResponse(BaseModel):
    """Ответ /v3/finance/transaction/list"""
    model_config = ConfigDict(extra='allow')

    result: OzonFinanceResult


# --- Supply Orders (/v3/supply-order/list, /v3/supply-order/get) ---

class OzonSupplyOrderListResponse(BaseModel):
    """Ответ /v3/supply-order/list"""
    model_config = ConfigDict(extra='allow')

    order_ids: List[int]
    last_id: Optional[str] = None  # Для пагинации (base64 строка)


class OzonSupplyTimeslot(BaseModel):
    """Временной слот поставки"""
    model_config = ConfigDict(extra='allow')

    from_: Optional[str] = Field(None, alias='from')
    to: Optional[str] = None


class OzonSupply(BaseModel):
    """Поставка"""
    model_config = ConfigDict(extra='allow')

    bundle_id: Optional[str] = None
    timeslot: Optional[OzonSupplyTimeslot] = None


class OzonDropOffWarehouse(BaseModel):
    """Склад приёмки"""
    model_config = ConfigDict(extra='allow')

    name: Optional[str] = None


class OzonSupplyOrder(BaseModel):
    """Заявка на поставку"""
    model_config = ConfigDict(extra='allow')

    order_id: int
    order_number: Optional[str] = None
    state: Optional[str] = None
    created_date: Optional[str] = None
    state_updated_date: Optional[str] = None
    supplies: Optional[List[OzonSupply]] = None
    drop_off_warehouse: Optional[OzonDropOffWarehouse] = None


class OzonSupplyOrderGetResponse(BaseModel):
    """Ответ /v3/supply-order/get"""
    model_config = ConfigDict(extra='allow')

    orders: List[OzonSupplyOrder]


# --- Supply Bundle (/v1/supply-order/bundle) ---

class OzonBundleItem(BaseModel):
    """Товар в поставке"""
    model_config = ConfigDict(extra='allow')

    offer_id: Optional[str] = None
    product_id: Optional[int] = None
    sku: Optional[int] = None
    barcode: Optional[str] = None
    name: Optional[str] = None
    quantity: Optional[int] = None


class OzonBundleResponse(BaseModel):
    """Ответ /v1/supply-order/bundle"""
    model_config = ConfigDict(extra='allow')

    items: List[OzonBundleItem]
    has_next: Optional[bool] = None
    last_id: Optional[str] = None


# --- Report Create (/v1/report/products/create) ---

class OzonReportCreateResult(BaseModel):
    """Результат создания отчёта"""
    model_config = ConfigDict(extra='allow')

    code: str


class OzonReportCreateResponse(BaseModel):
    """Ответ /v1/report/products/create"""
    model_config = ConfigDict(extra='allow')

    result: OzonReportCreateResult


# --- Report Info (/v1/report/info) ---

class OzonReportInfoResult(BaseModel):
    """Результат получения информации об отчёте"""
    model_config = ConfigDict(extra='allow')

    status: str
    file: Optional[str] = None
    error: Optional[str] = None


class OzonReportInfoResponse(BaseModel):
    """Ответ /v1/report/info"""
    model_config = ConfigDict(extra='allow')

    result: OzonReportInfoResult


# ==============================================================================
# Wildberries API Schemas
# ==============================================================================

# --- Statistics: Incomes ---

class WBIncome(BaseModel):
    """Поступление WB"""
    model_config = ConfigDict(extra='allow')

    incomeId: int
    number: Optional[str] = None
    date: str
    lastChangeDate: Optional[str] = None
    supplierArticle: Optional[str] = None
    nmId: Optional[int] = None
    barcode: Optional[str] = None
    quantity: Optional[int] = None
    totalPrice: Optional[float] = None
    dateClose: Optional[str] = None
    warehouseName: Optional[str] = None
    status: Optional[str] = None


# --- Statistics: Sales ---

class WBSale(BaseModel):
    """Продажа WB"""
    model_config = ConfigDict(extra='allow')

    srid: str
    date: str
    lastChangeDate: Optional[str] = None
    supplierArticle: Optional[str] = None
    nmId: Optional[int] = None
    barcode: Optional[str] = None
    totalPrice: Optional[float] = None
    discountPercent: Optional[int] = None
    spp: Optional[float] = None
    forPay: Optional[float] = None
    finishedPrice: Optional[float] = None
    priceWithDisc: Optional[float] = None
    warehouseName: Optional[str] = None
    regionName: Optional[str] = None
    countryName: Optional[str] = None
    oblastOkrugName: Optional[str] = None
    saleID: Optional[str] = None
    gNumber: Optional[str] = None


# --- Statistics: Orders ---

class WBOrder(BaseModel):
    """Заказ WB"""
    model_config = ConfigDict(extra='allow')

    srid: str
    date: str
    lastChangeDate: Optional[str] = None
    supplierArticle: Optional[str] = None
    nmId: Optional[int] = None
    barcode: Optional[str] = None
    totalPrice: Optional[float] = None
    discountPercent: Optional[int] = None
    spp: Optional[float] = None
    finishedPrice: Optional[float] = None
    warehouseName: Optional[str] = None
    regionName: Optional[str] = None
    isCancel: Optional[bool] = None
    cancelDate: Optional[str] = None
    gNumber: Optional[str] = None


# --- Statistics: Stocks ---

class WBStock(BaseModel):
    """Остаток WB"""
    model_config = ConfigDict(extra='allow')

    barcode: str
    warehouseName: Optional[str] = None
    quantity: Optional[int] = None
    quantityFull: Optional[int] = None
    inWayToClient: Optional[int] = None
    inWayFromClient: Optional[int] = None
    nmId: Optional[int] = None
    supplierArticle: Optional[str] = None


# --- Content API: Cards ---

class WBCardPhoto(BaseModel):
    """Фото карточки"""
    model_config = ConfigDict(extra='allow')

    big: Optional[str] = None
    c246x328: Optional[str] = None
    c516x688: Optional[str] = None


class WBCardSize(BaseModel):
    """Размер в карточке"""
    model_config = ConfigDict(extra='allow')

    techSize: Optional[str] = None
    wbSize: Optional[str] = None
    skus: Optional[List[str]] = None


class WBCard(BaseModel):
    """Карточка товара WB"""
    model_config = ConfigDict(extra='allow')

    vendorCode: Optional[str] = None
    brand: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    photos: Optional[List[WBCardPhoto]] = None
    sizes: Optional[List[WBCardSize]] = None


class WBCardsCursor(BaseModel):
    """Курсор для пагинации"""
    model_config = ConfigDict(extra='allow')

    updatedAt: Optional[str] = None
    nmID: Optional[int] = None


class WBCardsListResponse(BaseModel):
    """Ответ /content/v2/get/cards/list"""
    model_config = ConfigDict(extra='allow')

    cards: List[WBCard]
    cursor: Optional[WBCardsCursor] = None


# ==============================================================================
# Validation Functions
# ==============================================================================

def validate_ozon_fbs_list(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v3/posting/fbs/list"""
    try:
        validated = OzonFBSListResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonFBSListResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_ozon_fbo_list(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v2/posting/fbo/list"""
    try:
        validated = OzonFBOListResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonFBOListResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_ozon_finance(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v3/finance/transaction/list"""
    try:
        validated = OzonFinanceResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonFinanceResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_ozon_supply_list(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v3/supply-order/list"""
    try:
        validated = OzonSupplyOrderListResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonSupplyOrderListResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_ozon_supply_get(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v3/supply-order/get"""
    try:
        validated = OzonSupplyOrderGetResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonSupplyOrderGetResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_ozon_bundle(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа /v1/supply-order/bundle"""
    try:
        validated = OzonBundleResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, OzonBundleResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_wb_incomes(response_data: list) -> tuple[bool, str, list]:
    """Валидация ответа WB incomes"""
    try:
        if not response_data:
            return True, "OK (empty)", []
        for item in response_data[:5]:  # Проверяем первые 5
            WBIncome(**item)
        extra_fields = _get_extra_fields_list(response_data, WBIncome)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_wb_sales(response_data: list) -> tuple[bool, str, list]:
    """Валидация ответа WB sales"""
    try:
        if not response_data:
            return True, "OK (empty)", []
        for item in response_data[:5]:
            WBSale(**item)
        extra_fields = _get_extra_fields_list(response_data, WBSale)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_wb_orders(response_data: list) -> tuple[bool, str, list]:
    """Валидация ответа WB orders"""
    try:
        if not response_data:
            return True, "OK (empty)", []
        for item in response_data[:5]:
            WBOrder(**item)
        extra_fields = _get_extra_fields_list(response_data, WBOrder)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_wb_stocks(response_data: list) -> tuple[bool, str, list]:
    """Валидация ответа WB stocks"""
    try:
        if not response_data:
            return True, "OK (empty)", []
        for item in response_data[:5]:
            WBStock(**item)
        extra_fields = _get_extra_fields_list(response_data, WBStock)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def validate_wb_cards(response_data: dict) -> tuple[bool, str, list]:
    """Валидация ответа WB cards"""
    try:
        validated = WBCardsListResponse(**response_data)
        extra_fields = _get_extra_fields(response_data, WBCardsListResponse)
        return True, "OK", extra_fields
    except Exception as e:
        return False, str(e), []


def _get_extra_fields(data: dict, model: type) -> list:
    """Получить список полей в данных, которых нет в модели"""
    if not isinstance(data, dict):
        return []

    model_fields = set(model.model_fields.keys())
    data_fields = set(data.keys())
    extra = data_fields - model_fields

    # Рекурсивно проверяем вложенные объекты
    result = [f"root.{f}" for f in extra]

    return result


def _get_extra_fields_list(data: list, model: type) -> list:
    """Получить список полей из списка объектов"""
    if not data:
        return []

    model_fields = set(model.model_fields.keys())
    all_extra = set()

    for item in data[:10]:  # Проверяем первые 10
        if isinstance(item, dict):
            extra = set(item.keys()) - model_fields
            all_extra.update(extra)

    return list(all_extra)
