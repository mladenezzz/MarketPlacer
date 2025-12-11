# Wildberries API — Полная документация

Base URL: `https://{service}-api.wildberries.ru`

---

## Содержание

1. [Общее (API Information)](#общее-api-information)
2. [Контент](#контент)
3. [Цены и скидки](#цены-и-скидки)
4. [Склады и остатки](#склады-и-остатки)
5. [Заказы FBS](#заказы-fbs)
6. [Поставки FBW](#поставки-fbw)
7. [Заказы DBW](#заказы-dbw)
8. [Заказы DBS](#заказы-dbs)
9. [Самовывоз](#самовывоз)
10. [Аналитика](#аналитика)
11. [Продвижение](#продвижение)
12. [Отзывы и вопросы](#отзывы-и-вопросы)
13. [Чат с покупателями](#чат-с-покупателями)
14. [Тарифы](#тарифы)
15. [Отчёты](#отчёты)
16. [Документы и финансы](#документы-и-финансы)

---

## Общее (API Information)

**Base URL:** `https://common-api.wildberries.ru`

### Ping — Проверка подключения

| Параметр | Значение |
|----------|----------|
| **Метод** | `GET` |
| **Endpoint** | `/ping` |
| **Лимит** | 3 запроса / 30 сек |

**Base URLs по сервисам:**
- Контент: `https://content-api.wildberries.ru/ping`
- Аналитика: `https://seller-analytics-api.wildberries.ru/ping`
- Цены: `https://discounts-prices-api.wildberries.ru/ping`
- Маркетплейс: `https://marketplace-api.wildberries.ru/ping`
- Статистика: `https://statistics-api.wildberries.ru/ping`
- Продвижение: `https://advert-api.wildberries.ru/ping`
- Отзывы: `https://feedbacks-api.wildberries.ru/ping`
- Чат: `https://buyer-chat-api.wildberries.ru/ping`
- Поставки: `https://supplies-api.wildberries.ru/ping`
- Возвраты: `https://returns-api.wildberries.ru/ping`
- Документы: `https://documents-api.wildberries.ru/ping`
- Финансы: `https://finance-api.wildberries.ru/ping`

**Ответ (200):**
```json
{ "TS": "2024-08-16T11:19:05+03:00", "Status": "OK" }
```

---

### Новости портала

| Параметр | Значение |
|----------|----------|
| **Метод** | `GET` |
| **Endpoint** | `/api/communications/v2/news` |
| **Лимит** | 1 запрос / мин |

**Query:** `from` (date), `fromID` (int) — минимум один обязателен

**Ответ (200):**
```json
{
  "data": [
    {
      "id": 7369,
      "content": "string",
      "date": "2025-02-05T14:10:35+03:00",
      "header": "string",
      "types": [{ "id": 4, "name": "Маркетинг" }]
    }
  ]
}
```

---

### Информация о продавце

| Параметр | Значение |
|----------|----------|
| **Метод** | `GET` |
| **Endpoint** | `/api/v1/seller-info` |
| **Лимит** | 1 запрос / мин |

**Ответ (200):**
```json
{ "name": "ИП Иванов И.И.", "sid": "uuid", "tradeMark": "Brand" }
```

---

### Управление пользователями

**Base URL:** `https://user-management-api.wildberries.ru`

#### POST `/api/v1/invite` — Создать приглашение

**Ответ (200):**
```json
{
  "inviteID": "uuid",
  "expiredAt": "2025-10-06T10:56:04Z",
  "isSuccess": true,
  "inviteUrl": "https://seller.wildberries.ru/..."
}
```

#### GET `/api/v1/users` — Список пользователей

**Ответ (200):**
```json
{
  "total": 2,
  "countInResponse": 2,
  "users": [{
    "id": 123,
    "role": "user",
    "position": "string",
    "phone": "string",
    "email": "string",
    "isOwner": false,
    "isInvitee": false,
    "access": [{ "code": "finance", "disabled": false }]
  }]
}
```

#### PUT `/api/v1/users/access` — Изменить права
**Ответ (200):** Пустое тело

#### DELETE `/api/v1/user` — Удалить пользователя
**Ответ (200):** Пустое тело

---

## Контент

**Base URL:** `https://content-api.wildberries.ru`

### Справочники

#### GET `/content/v2/object/parent/all` — Родительские категории

**Ответ (200):**
```json
{
  "data": [{ "name": "string", "id": 123, "isVisible": true }],
  "error": false,
  "errorText": ""
}
```

#### GET `/content/v2/object/all` — Список предметов

**Query:** `locale`, `name`, `limit`, `offset`, `parentID`

**Ответ (200):**
```json
{
  "data": [{
    "subjectID": 123,
    "parentID": 456,
    "subjectName": "string",
    "parentName": "string"
  }],
  "error": false
}
```

#### GET `/content/v2/object/charcs/{subjectId}` — Характеристики предмета

**Ответ (200):**
```json
{
  "data": [{
    "charcID": 123,
    "name": "string",
    "required": true,
    "unitName": "string",
    "maxCount": 10,
    "charcType": 1
  }],
  "error": false
}
```

---

### Карточки товаров

#### GET `/content/v2/cards/limits` — Лимиты карточек

**Ответ (200):**
```json
{
  "data": {
    "freeLimits": { "numberOfCards": 100 },
    "paidLimits": { "numberOfCards": 1000 }
  }
}
```

#### POST `/content/v2/barcodes` — Генерация баркодов

**Body:** `{ "count": 10 }`

**Ответ (200):**
```json
{ "data": ["2000000000001", "2000000000002"] }
```

#### POST `/content/v2/get/cards/list` — Список карточек

**Ответ (200):**
```json
{
  "cards": [{
    "nmID": 123456789,
    "imtID": 987654321,
    "vendorCode": "ABC123",
    "title": "Товар",
    "brand": "Brand",
    "sizes": [{ "chrtID": 111, "techSize": "M", "skus": ["sku1"] }],
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-02T00:00:00Z"
  }],
  "cursor": { "updatedAt": "datetime", "nmID": 123, "total": 100 }
}
```

#### POST `/content/v2/cards/upload` — Создание карточек
**Ответ (200):** `{ "error": false, "errorText": "" }`

#### POST `/content/v2/cards/update` — Редактирование
**Ответ (200):** `{ "error": false, "errorText": "" }`

---

### Медиафайлы

#### POST `/content/v3/media/file` — Загрузить файл

**Headers:** `X-Nm-Id`, `X-Photo-Number`

**Ответ (200):** `{ "error": false, "errorText": "" }`

---

### Ярлыки

#### GET `/content/v2/tags` — Список ярлыков

**Ответ (200):**
```json
{
  "data": [{ "id": 1, "name": "Хит", "color": "#FF0000" }],
  "error": false
}
```

#### POST `/content/v2/tag` — Создание ярлыка

**Body:** `{ "name": "Новинка", "color": "#00FF00" }`

**Ответ (200):** `{ "data": { "id": 2 }, "error": false }`

---

## Цены и скидки

**Base URL:** `https://discounts-prices-api.wildberries.ru`

#### POST `/api/v2/upload/task` — Установить цены и скидки

**Body:**
```json
{ "data": [{ "nmID": 123, "price": 1000, "discount": 10 }] }
```

**Ответ (200):**
```json
{
  "data": { "id": 12345, "alreadyExists": false },
  "error": false
}
```

#### GET `/api/v2/history/tasks` — Состояние загрузки

**Query:** `uploadID`

**Ответ (200):**
```json
{
  "data": {
    "uploadID": 12345,
    "status": 3,
    "uploadDate": "datetime",
    "activationDate": "datetime",
    "overAllGoodsNumber": 100,
    "successGoodsNumber": 98
  }
}
```

#### GET `/api/v2/list/goods/filter` — Товары с ценами

**Query:** `limit`, `offset`, `filterNmID`

**Ответ (200):**
```json
{
  "data": {
    "listGoods": [{
      "nmID": 123,
      "vendorCode": "ABC",
      "sizes": [{
        "sizeID": 1,
        "price": 1000,
        "discountedPrice": 900,
        "techSizeName": "M"
      }],
      "currencyIsoCode4217": "RUB",
      "discount": 10,
      "editableSizePrice": true
    }]
  }
}
```

---

## Склады и остатки

**Base URL:** `https://marketplace-api.wildberries.ru`

### Склады

#### GET `/api/v3/offices` — Список складов WB

**Ответ (200):**
```json
[{ "id": 507, "name": "Коледино", "address": "...", "city": "Москва" }]
```

#### GET `/api/v3/warehouses` — Склады продавца

**Ответ (200):**
```json
[{ "id": 123, "name": "Мой склад", "officeId": 507 }]
```

#### POST `/api/v3/warehouses` — Создать склад

**Ответ (200):** `{ "id": 124 }`

---

### Остатки

#### POST `/api/v3/stocks/{warehouseId}` — Получить остатки

**Ответ (200):**
```json
{
  "stocks": [{ "chrtId": 111, "sku": "sku1", "amount": 50 }]
}
```

#### PUT `/api/v3/stocks/{warehouseId}` — Обновить остатки
**Ответ (200):** Пустое тело (204)

---

## Заказы FBS

**Base URL:** `https://marketplace-api.wildberries.ru`

### Сборочные задания

#### GET `/api/v3/orders/new` — Новые задания

**Ответ (200):**
```json
{
  "orders": [{
    "id": 13833711,
    "rid": "string",
    "createdAt": "2022-05-04T07:56:29Z",
    "warehouseId": 658434,
    "nmId": 123456789,
    "chrtId": 987654321,
    "price": 1014,
    "salePrice": 900,
    "article": "ABC123",
    "colorCode": "RAL 3017",
    "cargoType": 1,
    "address": {
      "fullAddress": "string",
      "longitude": 44.5,
      "latitude": 40.2
    },
    "requiredMeta": ["sgtin"],
    "deliveryType": "fbs"
  }]
}
```

#### GET `/api/v3/orders` — Информация о заданиях

**Query:** `limit` (1-1000), `next`, `dateFrom`, `dateTo` (Unix)

**Ответ (200):**
```json
{
  "next": 13833712,
  "orders": [{
    "id": 13833711,
    "supplyId": "WB-GI-123",
    "createdAt": "datetime",
    "nmId": 123,
    "chrtId": 456,
    "price": 1000
  }]
}
```

#### POST `/api/v3/orders/status` — Статусы заданий

**Body:** `{ "orders": [123, 456] }`

**Ответ (200):**
```json
{
  "orders": [{
    "id": 123,
    "supplierStatus": "new|confirm|complete|cancel",
    "wbStatus": "waiting|sorted|sold|canceled"
  }]
}
```

#### POST `/api/v3/orders/stickers` — Стикеры заданий

**Query:** `type` (svg/zplv/zplh/png), `width`, `height`

**Ответ (200):**
```json
{
  "stickers": [{
    "orderId": 123,
    "partA": "231648",
    "partB": "9753",
    "barcode": "string",
    "file": "base64_encoded"
  }]
}
```

---

### Метаданные FBS

#### POST `/api/marketplace/v3/orders/meta` — Получить метаданные

**Ответ (200):**
```json
{
  "orders": [{
    "id": 123,
    "meta": {
      "imei": { "value": "123456789012345" },
      "uin": { "value": "1234567890123456" },
      "gtin": { "value": "1234567890123" },
      "sgtin": { "value": ["code1", "code2"] },
      "expiration": { "value": "01.01.2025" }
    }
  }]
}
```

---

### Поставки FBS

#### POST `/api/v3/supplies` — Создать поставку

**Body:** `{ "name": "Поставка 1" }`

**Ответ (200):** `{ "id": "WB-GI-1234567" }`

#### GET `/api/v3/supplies` — Список поставок

**Ответ (200):**
```json
{
  "next": 123,
  "supplies": [{
    "id": "WB-GI-123",
    "done": false,
    "createdAt": "datetime",
    "closedAt": null,
    "name": "Поставка 1",
    "cargoType": 1
  }]
}
```

#### GET `/api/v3/supplies/{supplyId}` — Информация о поставке

**Ответ (200):**
```json
{
  "id": "WB-GI-123",
  "done": true,
  "createdAt": "datetime",
  "closedAt": "datetime",
  "name": "Поставка 1",
  "cargoType": 1,
  "scanDt": "datetime"
}
```

---

### Короба FBS

#### GET `/api/v3/supplies/{supplyId}/trbx` — Список коробов

**Ответ (200):**
```json
{ "trbxes": [{ "id": "WB-TRBX-1234567" }] }
```

#### POST `/api/v3/supplies/{supplyId}/trbx/stickers` — Стикеры коробов

**Ответ (200):**
```json
{
  "stickers": [{ "barcode": "string", "file": "base64_encoded" }]
}
```

---

## Поставки FBW

**Base URL:** `https://supplies-api.wildberries.ru`

#### POST `/api/v1/acceptance/options` — Опции приёмки

**Ответ (200):**
```json
{
  "result": [{
    "barcode": "123456789",
    "warehouses": [{
      "warehouseID": 205349,
      "canBox": true,
      "canMonopallet": false
    }]
  }],
  "requestId": "uuid"
}
```

#### GET `/api/v1/warehouses` — Список складов WB

**Ответ (200):**
```json
[{
  "ID": 300461,
  "name": "Гомель 2",
  "address": "string",
  "workTime": "24/7",
  "isActive": true
}]
```

#### GET `/api/v1/transit-tariffs` — Транзитные направления

**Ответ (200):**
```json
[{
  "transitWarehouseName": "Обухово",
  "destinationWarehouseName": "Краснодар",
  "activeFrom": "datetime",
  "boxTariff": null,
  "palletTariff": 7500
}]
```

#### POST `/api/v1/supplies` — Список поставок

**Ответ (200):**
```json
[{
  "phone": "+7 916 *** 44 44",
  "supplyID": "string",
  "preorderID": 34597755,
  "createDate": "datetime",
  "statusID": 1
}]
```

#### GET `/api/v1/supplies/{ID}` — Детали поставки

**Ответ (200):**
```json
{
  "phone": "string",
  "statusID": 5,
  "boxTypeID": 5,
  "warehouseID": 507,
  "warehouseName": "Коледино",
  "quantity": 10,
  "acceptedQuantity": 10
}
```

#### GET `/api/v1/supplies/{ID}/goods` — Товары поставки

**Ответ (200):**
```json
[{
  "barcode": "1234567891234",
  "vendorCode": "ABC",
  "nmID": 987456654,
  "needKiz": true,
  "quantity": 10
}]
```

---

## Заказы DBW

**Base URL:** `https://marketplace-api.wildberries.ru`

#### GET `/api/v3/dbw/orders/new` — Новые задания

**Ответ (200):**
```json
{
  "orders": [{
    "id": 13833711,
    "warehouseId": 658434,
    "nmId": 123456789,
    "chrtId": 987654321,
    "price": 1014,
    "salePrice": 900,
    "createdAt": "datetime",
    "article": "string",
    "groupId": "uuid",
    "address": { "fullAddress": "string", "longitude": 0.0, "latitude": 0.0 },
    "cargoType": 1
  }]
}
```

#### POST `/api/v3/dbw/orders/status` — Статусы заданий

**Ответ (200):**
```json
{
  "orders": [{ "id": 123, "supplierStatus": "new", "wbStatus": "string" }]
}
```

#### POST `/api/v3/dbw/orders/stickers` — Стикеры

**Ответ (200):**
```json
{
  "stickers": [{
    "orderId": 123,
    "partA": "231648",
    "partB": "9753",
    "barcode": "string",
    "file": "base64_encoded"
  }]
}
```

#### POST `/api/v3/dbw/orders/courier` — Информация о курьере

**Ответ (200):**
```json
{
  "orders": [{
    "orderID": 123,
    "courierInfo": {
      "contacts": {
        "carNumber": "х111хх11",
        "fullName": "string",
        "phone": 71230971931
      },
      "pTimeFrom": "datetime",
      "pTimeTo": "datetime"
    }
  }]
}
```

#### GET `/api/v3/dbw/orders/{orderId}/meta` — Метаданные

**Ответ (200):**
```json
{
  "meta": {
    "imei": { "value": "123456789012345" },
    "uin": { "value": "1234567890123456" },
    "gtin": { "value": "1234567890123" },
    "sgtin": { "value": ["code1"] }
  }
}
```

---

## Заказы DBS

**Base URL:** `https://marketplace-api.wildberries.ru`

#### GET `/api/v3/dbs/orders/new` — Новые задания

**Ответ (200):**
```json
{
  "orders": [{
    "id": 13833711,
    "warehouseId": 658434,
    "nmId": 123456789,
    "chrtId": 987654321,
    "price": 1014,
    "finalPrice": 900,
    "createdAt": "datetime",
    "deliveryType": "dbs",
    "address": { "fullAddress": "string", "longitude": 0.0, "latitude": 0.0 },
    "requiredMeta": ["uin"],
    "comment": "string"
  }]
}
```

#### POST `/api/v3/dbs/orders/client` — Информация о клиенте

**Ответ (200):**
```json
{
  "orders": [{
    "orderID": 134567,
    "phone": "+79871234567",
    "firstName": "Иван",
    "fullName": "Иван Иванович",
    "phoneCode": 1234567
  }]
}
```

#### POST `/api/v3/dbs/groups/info` — Платная доставка

**Ответ (200):**
```json
[{
  "groupID": "uuid",
  "deliveryCost": 1108,
  "currencyCode": 643
}]
```

---

## Самовывоз

**Base URL:** `https://marketplace-api.wildberries.ru`

#### GET `/api/v3/click-collect/orders/new` — Новые задания

**Ответ (200):**
```json
{
  "orders": [{
    "id": 123,
    "nmId": 456,
    "chrtId": 789,
    "price": 1000,
    "createdAt": "datetime",
    "article": "string"
  }]
}
```

#### POST `/api/v3/click-collect/orders/client` — Информация о клиенте

**Ответ (200):**
```json
{
  "orders": [{
    "orderID": 123,
    "phone": "+79871234567",
    "name": "Иван"
  }]
}
```

#### POST `/api/v3/click-collect/orders/client/identity` — Проверка по паролю

**Body:** `{ "orderCode": "string", "passcode": "string" }`

**Ответ (200):** `{ "isValid": true }`

---

## Аналитика

**Base URL:** `https://seller-analytics-api.wildberries.ru`

### Воронка продаж

#### POST `/api/analytics/v3/sales-funnel/products` — Статистика товаров

**Ответ (200):**
```json
{
  "data": {
    "products": [{
      "product": {
        "nmId": 268913787,
        "title": "Товар",
        "vendorCode": "12345",
        "brandName": "Brand",
        "subjectId": 105,
        "subjectName": "Категория",
        "productRating": 4.5
      },
      "statistic": {
        "selected": {
          "period": { "start": "2023-06-01", "end": "2024-03-01" },
          "openCount": 45,
          "cartCount": 34,
          "orderCount": 19,
          "orderSum": 1262,
          "buyoutCount": 19,
          "conversions": {
            "addToCartPercent": 19,
            "cartToOrderPercent": 65,
            "buyoutPercent": 100
          }
        }
      }
    }]
  }
}
```

#### POST `/api/analytics/v3/sales-funnel/products/history` — По дням

**Ответ (200):**
```json
[{
  "product": { "nmId": 123, "title": "string" },
  "history": [{
    "date": "2024-10-23",
    "openCount": 45,
    "cartCount": 34,
    "orderCount": 19,
    "orderSum": 1262
  }]
}]
```

---

### Поисковые запросы

#### POST `/api/v2/search-report/report` — Основной отчёт

**Ответ (200):**
```json
{
  "data": {
    "commonInfo": {
      "supplierRating": { "current": 5.3, "dynamics": 5.4 },
      "totalProducts": 150
    },
    "positionInfo": {
      "average": { "current": 5, "dynamics": 50 },
      "median": { "current": 5, "dynamics": 50 }
    },
    "groups": []
  }
}
```

---

### CSV-отчёты

#### POST `/api/v2/nm-report/downloads` — Создать отчёт

**Ответ (200):** `{ "data": "Created" }`

#### GET `/api/v2/nm-report/downloads` — Список отчётов

**Ответ (200):**
```json
{
  "data": [{
    "id": "uuid",
    "createdAt": "datetime",
    "status": "SUCCESS",
    "name": "Report",
    "size": 123,
    "startDate": "2024-06-21",
    "endDate": "2024-06-23"
  }]
}
```

---

## Продвижение

**Base URL:** `https://advert-api.wildberries.ru`

### Кампании

#### GET `/adv/v1/promotion/count` — Списки кампаний

**Ответ (200):**
```json
{
  "adverts": [{
    "type": 9,
    "status": 8,
    "count": 3,
    "advert_list": [{ "advertId": 6485174, "changeTime": "datetime" }]
  }],
  "all": 3
}
```

#### POST `/adv/v1/promotion/adverts` — Информация о кампаниях

**Ответ (200):**
```json
[{
  "advertId": 11111111,
  "name": "Кампания1",
  "status": 7,
  "type": 8,
  "paymentType": "cpm",
  "createTime": "datetime",
  "startTime": "datetime",
  "endTime": "datetime"
}]
```

#### POST `/adv/v0/bids/min` — Минимальные ставки

**Ответ (200):**
```json
{
  "bids": [{
    "nm_id": 12345678,
    "bids": [
      { "type": "combined", "value": 155 },
      { "type": "search", "value": 250 }
    ]
  }]
}
```

---

### Финансы продвижения

#### GET `/adv/v1/balance` — Баланс

**Ответ (200):**
```json
{ "balance": 10000, "bonus": 500 }
```

#### GET `/adv/v1/budget` — Бюджет кампании

**Query:** `id`

**Ответ (200):**
```json
{ "total": 50000, "dailyBudget": 5000, "spent": 15000 }
```

---

### Статистика продвижения

#### GET `/adv/v3/fullstats` — Статистика кампаний

**Query:** `ids`, `beginDate`, `endDate`

**Ответ (200):**
```json
[{
  "advertId": 123,
  "dates": [{
    "date": "2024-01-01",
    "views": 1000,
    "clicks": 50,
    "ctr": 5.0,
    "cpc": 10,
    "sum": 500,
    "orders": 5,
    "cr": 10,
    "shks": 5,
    "sum_price": 5000
  }]
}]
```

---

## Отзывы и вопросы

**Base URL:** `https://feedbacks-api.wildberries.ru`

### Вопросы

#### GET `/api/v1/questions` — Список вопросов

**Ответ (200):**
```json
{
  "data": {
    "countUnanswered": 24,
    "questions": [{
      "id": "string",
      "text": "Question text",
      "createdDate": "datetime",
      "state": "suppliersPortalSynch",
      "answer": null,
      "productDetails": {
        "nmId": 14917842,
        "productName": "Product",
        "brandName": "Brand"
      },
      "wasViewed": false
    }]
  },
  "error": false
}
```

---

### Отзывы

#### GET `/api/v1/feedbacks` — Список отзывов

**Ответ (200):**
```json
{
  "data": {
    "countUnanswered": 52,
    "feedbacks": [{
      "id": "string",
      "text": "Отзыв",
      "pros": "Плюсы",
      "cons": "Минусы",
      "productValuation": 5,
      "createdDate": "datetime",
      "answer": { "text": "Ответ", "state": "wbRu", "editable": false },
      "productDetails": {
        "nmId": 987654321,
        "productName": "Product",
        "brandName": "Brand"
      },
      "photoLinks": [{ "fullSize": "url", "miniSize": "url" }],
      "userName": "Николай",
      "wasViewed": true
    }]
  },
  "error": false
}
```

---

## Чат с покупателями

**Base URL:** `https://buyer-chat-api.wildberries.ru`

#### GET `/api/v1/seller/events` — События чатов

**Ответ (200):**
```json
{
  "result": {
    "next": 1698045576000,
    "totalEvents": 4,
    "events": [{
      "chatID": "uuid",
      "eventID": "uuid",
      "eventType": "message",
      "message": { "text": "Сообщение" },
      "sender": "client",
      "addTime": "datetime",
      "clientID": "186132",
      "clientName": "Алёна"
    }]
  }
}
```

---

### Возвраты покупателями

**Base URL:** `https://returns-api.wildberries.ru`

#### GET `/api/v1/claims` — Заявки на возврат

**Ответ (200):**
```json
{
  "claims": [{
    "id": 123,
    "nmId": 456,
    "status": "pending",
    "createdAt": "datetime",
    "comment": "string"
  }]
}
```

---

## Тарифы

**Base URL:** `https://common-api.wildberries.ru`

#### GET `/api/v1/tariffs/commission` — Комиссия по категориям

**Ответ (200):**
```json
{
  "report": [{
    "parentID": 657,
    "parentName": "Категория",
    "subjectID": 6461,
    "subjectName": "Подкатегория",
    "kgvpMarketplace": 15.5,
    "kgvpSupplier": 12.5,
    "paidStorageKgvp": 15.5
  }]
}
```

#### GET `/api/v1/tariffs/box` — Тарифы для коробов

**Query:** `date` (ГГГГ-ММ-ДД)

**Ответ (200):**
```json
{
  "response": {
    "data": {
      "dtNextBox": "2024-02-01",
      "warehouseList": [{
        "warehouseName": "string",
        "boxDeliveryBase": "48",
        "boxDeliveryLiter": "11,2",
        "boxStorageBase": "0,14"
      }]
    }
  }
}
```

#### GET `/api/tariffs/v1/acceptance/coefficients` — Тарифы на поставку

**Ответ (200):**
```json
[{
  "date": "datetime",
  "coefficient": -1,
  "warehouseID": 217081,
  "warehouseName": "string",
  "allowUnload": false,
  "boxTypeID": 6
}]
```

---

## Отчёты

**Base URL:** `https://statistics-api.wildberries.ru`

### Основные

#### GET `/api/v1/supplier/incomes` — Поставки

**Ответ (200):**
```json
[{
  "incomeId": 12345,
  "date": "datetime",
  "supplierArticle": "ABCDEF",
  "barcode": "2000328074123",
  "quantity": 3,
  "warehouseName": "Подольск",
  "nmId": 1234567,
  "status": "Принято"
}]
```

#### GET `/api/v1/supplier/stocks` — Остатки на складах

**Ответ (200):**
```json
[{
  "lastChangeDate": "datetime",
  "warehouseName": "Краснодар",
  "supplierArticle": "443284",
  "nmId": 1439871458,
  "barcode": "2037401340280",
  "quantity": 33,
  "inWayToClient": 1,
  "inWayFromClient": 0,
  "Price": 185,
  "Discount": 0
}]
```

---

### Асинхронные отчёты

#### GET `/api/v1/warehouse_remains` — Создать отчёт

**Ответ (200):**
```json
{ "data": { "taskId": "uuid" } }
```

#### GET `/api/v1/warehouse_remains/tasks/{task_id}/status` — Статус

**Ответ (200):**
```json
{ "data": { "id": "uuid", "status": "done" } }
```

#### GET `/api/v1/warehouse_remains/tasks/{task_id}/download` — Скачать

**Ответ (200):**
```json
[{
  "brand": "Brand",
  "subjectName": "Категория",
  "vendorCode": "ABC",
  "nmId": 183804172,
  "barcode": "string",
  "techSize": "0",
  "volume": 1.33,
  "warehouses": [{ "warehouseName": "Коледино", "quantity": 134 }]
}]
```

---

### Продажи по регионам

#### GET `/api/v1/analytics/region-sale` — Отчёт

**Ответ (200):**
```json
{
  "report": [{
    "cityName": "Москва",
    "countryName": "Россия",
    "regionName": "Московская область",
    "nmID": 177974431,
    "saleInvoiceCostPrice": 592.11,
    "saleItemInvoiceQty": 4
  }]
}
```

---

## Документы и финансы

### Финансы

**Base URL:** `https://finance-api.wildberries.ru`

#### GET `/api/v1/account/balance` — Баланс продавца

**Ответ (200):**
```json
{ "balance": 50000, "currency": "RUB", "availableForWithdraw": 45000 }
```

---

### Отчёт о реализации

**Base URL:** `https://statistics-api.wildberries.ru`

#### GET `/api/v5/supplier/reportDetailByPeriod` — Детализация

**Query:** `dateFrom`, `dateTo` (RFC3339), `limit`, `rrdid`

**Ответ (200):**
```json
[{
  "realizationreport_id": 123,
  "date_from": "datetime",
  "date_to": "datetime",
  "nm_id": 456,
  "barcode": "string",
  "doc_type_name": "Продажа",
  "quantity": 1,
  "retail_price": 1000,
  "sale_percent": 15,
  "commission_percent": 10,
  "ppvz_for_pay": 850
}]
```

---

### Документы

**Base URL:** `https://documents-api.wildberries.ru`

#### GET `/api/v1/documents/categories` — Категории

**Ответ (200):**
```json
[{ "id": 1, "name": "Акты" }, { "id": 2, "name": "Счета" }]
```

#### GET `/api/v1/documents/list` — Список документов

**Ответ (200):**
```json
{
  "documents": [{
    "serviceName": "uuid",
    "name": "Акт",
    "category": "Акты",
    "createdAt": "datetime",
    "extensions": ["pdf", "xlsx"]
  }]
}
```
