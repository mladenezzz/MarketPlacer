# API маркетплейсов

Документация по всем используемым API методам маркетплейсов в проекте.

---

## Wildberries API

### 1. Поступления (Incomes)

- **Назначение:** Получение данных о поступлениях товаров на склад
- **HTTP метод:** GET
- **URL:** `https://statistics-api.wildberries.ru/api/v1/supplier/incomes`
- **Параметры:**
  - `dateFrom` — дата начала (YYYY-MM-DD)
- **Возвращаемые данные:** incomeId, number, date, lastChangeDate, supplierArticle, nmId, barcode, quantity, totalPrice, dateClose, warehouseName, status
- **Используется в:** `datacollector/collectors/wildberries.py:60-64`

---

### 2. Продажи (Sales)

- **Назначение:** Получение данных о продажах
- **HTTP метод:** GET
- **URL:** `https://statistics-api.wildberries.ru/api/v1/supplier/sales`
- **Параметры:**
  - `dateFrom` — дата начала (RFC3339: '2025-12-09T00:00:00.000Z')
  - `flag` — 0 = все данные от даты, 1 = данные за конкретную дату
- **Возвращаемые данные:** srid, date, lastChangeDate, supplierArticle, nmId, barcode, totalPrice, discountPercent, spp, forPay, finishedPrice, priceWithDisc, warehouseName, regionName, countryName, oblastOkrugName, saleID, gNumber
- **Используется в:** `datacollector/collectors/wildberries.py:171-175`, `app/services/marketplace_api.py:465-472`

---

### 3. Заказы (Orders)

- **Назначение:** Получение данных о заказах
- **HTTP метод:** GET
- **URL:** `https://statistics-api.wildberries.ru/api/v1/supplier/orders`
- **Параметры:**
  - `dateFrom` — дата начала (RFC3339)
  - `flag` — 0 = все данные от даты, 1 = данные за конкретную дату
- **Возвращаемые данные:** srid, date, lastChangeDate, supplierArticle, nmId, barcode, totalPrice, discountPercent, spp, finishedPrice, warehouseName, regionName, isCancel, cancelDate, gNumber
- **Используется в:** `datacollector/collectors/wildberries.py:261-265`, `app/services/marketplace_api.py:179-186`

---

### 4. Остатки (Stocks)

- **Назначение:** Получение данных об остатках на складах
- **HTTP метод:** GET
- **URL:** `https://statistics-api.wildberries.ru/api/v1/supplier/stocks`
- **Параметры:**
  - `dateFrom` — дата начала (YYYY-MM-DD)
- **Возвращаемые данные:** barcode, warehouseName, quantity, quantityFull, inWayToClient, inWayFromClient, nmId, supplierArticle
- **Используется в:** `datacollector/collectors/wildberries.py:324`

---

### 5. Карточки товаров (Content API)

- **Назначение:** Получение информации о карточках товаров с фото и размерами
- **HTTP метод:** POST
- **URL:** `https://content-api.wildberries.ru/content/v2/get/cards/list`
- **Тело запроса:**
```json
{
  "settings": {
    "cursor": {
      "limit": 100,
      "updatedAt": "2024-01-01T00:00:00Z",
      "nmID": 0
    },
    "filter": {
      "withPhoto": -1
    }
  }
}
```
- **Заголовки:** `Authorization: <API_TOKEN>`, `Content-Type: application/json`
- **Возвращаемые данные:** cards[] (vendorCode, brand, title, description, createdAt, updatedAt, photos[], sizes[]), cursor
- **Используется в:** `datacollector/collectors/wildberries.py:394-460`

---

## Ozon API

### 1. Создание отчета по товарам (Report Create)

- **Назначение:** Создание отчета по остаткам товаров (FBO + FBS)
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v1/report/products/create`
- **Тело запроса:**
```json
{
  "language": "DEFAULT",
  "offer_id": [],
  "search": "",
  "sku": [],
  "visibility": "ALL"
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** code (идентификатор отчета для скачивания)
- **Используется в:** `datacollector/collectors/ozon.py:103-124`

---

### 2. Информация об отчете (Report Info)

- **Назначение:** Получение статуса и URL файла отчета
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v1/report/info`
- **Тело запроса:**
```json
{
  "code": "report_code_string"
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** status (success/failed), file (URL для скачивания), error
- **Используется в:** `datacollector/collectors/ozon.py:141-156`

---

### 3. FBS заказы (Postings FBS List)

- **Назначение:** Получение заказов, отправляемых продавцом (Fulfillment by Seller)
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v3/posting/fbs/list`
- **Тело запроса:**
```json
{
  "dir": "ASC",
  "filter": {
    "since": "2025-12-09T00:00:00.000Z",
    "to": "2025-12-09T23:59:59.000Z",
    "status": ""
  },
  "limit": 1000,
  "offset": 0,
  "with": {
    "analytics_data": true,
    "financial_data": true
  }
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** postings[] (posting_number, order_id, order_number, status, in_process_at, shipment_date, products[], financial_data)
- **Используется в:** `datacollector/collectors/ozon.py:417-424`, `app/services/marketplace_api.py:307`

---

### 4. FBO заказы (Postings FBO List)

- **Назначение:** Получение заказов, отправляемых Ozon (Fulfillment by Ozon)
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v2/posting/fbo/list`
- **Тело запроса:** Аналогично FBS list
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** result[] (массив postings с той же структурой)
- **Используется в:** `datacollector/collectors/ozon.py:471-490`, `app/services/marketplace_api.py:308`

---

### 5. Финансовые транзакции (Finance Transactions)

- **Назначение:** Получение финансовых операций (продажи, начисления)
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v3/finance/transaction/list`
- **Тело запроса:**
```json
{
  "filter": {
    "date": {
      "from": "2025-12-01T00:00:00.000Z",
      "to": "2025-12-31T23:59:59.999Z"
    },
    "operation_type": ["OperationAgentDeliveredToCustomer"],
    "posting_number": "",
    "transaction_type": "all"
  },
  "page": 1,
  "page_size": 1000
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** operations[] (operation_id, operation_type, operation_date, amount, accruals_for_sale, posting{}, items[])
- **Используется в:** `datacollector/collectors/ozon.py:629-641`

---

### 6. Список поставок FBO (Supply Orders List)

- **Назначение:** Получение списка ID заявок на поставку
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v3/supply-order/list`
- **Тело запроса:**
```json
{
  "filter": {
    "states": ["COMPLETED"]
  },
  "limit": 100,
  "sort_by": 1
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** order_ids[], last_id (для пагинации)
- **Используется в:** `datacollector/collectors/ozon.py:769-789`

---

### 7. Детали поставок FBO (Supply Orders Get)

- **Назначение:** Получение информации о конкретных поставках
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v3/supply-order/get`
- **Тело запроса:**
```json
{
  "order_ids": [123, 456]
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** orders[] (order_id, order_number, state, created_date, state_updated_date, supplies{}, drop_off_warehouse{})
- **Используется в:** `datacollector/collectors/ozon.py:818`

---

### 8. Товары в поставке (Supply Order Bundle)

- **Назначение:** Получение товаров в конкретной поставке
- **HTTP метод:** POST
- **URL:** `https://api-seller.ozon.ru/v1/supply-order/bundle`
- **Тело запроса:**
```json
{
  "bundle_ids": ["bundle_id_string"],
  "limit": 100,
  "last_id": ""
}
```
- **Заголовки:** `Client-Id`, `Api-Key`, `Content-Type: application/json`
- **Возвращаемые данные:** items[] (offer_id, product_id, sku, barcode, name, quantity), has_next, last_id
- **Используется в:** `datacollector/collectors/ozon.py:895-924`

---

## Ограничения API

### Wildberries
- Параметр `dateTo` не поддерживается — данные фильтруются только по `dateFrom`
- Данные доступны до 6 месяцев назад
- Требуется задержка между запросами (rate limit)

### Ozon
- Максимальный период в одном запросе: до 30 дней
- Данные доступны до 3-6 месяцев назад
- Максимум 1000 записей в одном ответе
- Требуется пагинация для больших объемов данных
- При ошибке 429 — exponential backoff (2, 4, 8 секунд)

---

## Итого

| Маркетплейс | Количество методов |
|-------------|-------------------|
| Wildberries | 5 |
| Ozon | 8 |
| **Всего** | **13** |
