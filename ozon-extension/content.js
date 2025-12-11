/**
 * MarketPlacer Product Info Extension
 * Показывает информацию о товарах из базы при наведении на артикул
 * Поддержка: OZON и Wildberries
 */

(function() {
  'use strict';

  // Определяем текущий маркетплейс
  const CURRENT_HOST = window.location.hostname;
  const IS_OZON = CURRENT_HOST.includes('ozon.ru');
  const IS_WB = CURRENT_HOST.includes('wildberries.ru');
  const MARKETPLACE = IS_OZON ? 'ozon' : (IS_WB ? 'wb' : null);

  if (!MARKETPLACE) {
    console.log('[MarketPlacer Extension] Неизвестный маркетплейс, расширение не активировано');
    return;
  }

  // Конфигурация
  const CONFIG = {
    API_BASE: 'http://192.168.0.44:5000/api/extension',
    // Паттерн артикула для OZON: цифры (возможно с дефисами)/что-угодно
    // Примеры: 3035090018/658, 2089090018-14/11, 3009030003/M
    ARTICLE_PATTERN_OZON: /^[\d-]+\/[\w\d.,]+$/,
    // Паттерн артикула для WB: цифры с возможным дефисом и суффиксом
    // Примеры: 2013060166-1, 2013040628, 2013070222-2
    ARTICLE_PATTERN_WB: /^\d{7,}(-\d+)?$/,
    // Задержка перед показом тултипа (мс)
    HOVER_DELAY: 300,
    // Интервал сканирования новых элементов (мс)
    SCAN_INTERVAL: 2000
  };

  // Кеш артикулов из базы
  let articlesCache = new Set();
  let cacheLoaded = false;

  // Текущий тултип
  let tooltip = null;
  let hoverTimeout = null;
  let currentElement = null;

  // Кеш данных о товарах
  const productDataCache = new Map();

  /**
   * Загрузка списка артикулов из API (через background script)
   */
  async function loadArticles() {
    try {
      const data = await chrome.runtime.sendMessage({ action: 'fetchArticles' });

      if (data && data.success && data.articles) {
        articlesCache = new Set(data.articles);
        cacheLoaded = true;
        console.log(`[MarketPlacer Extension] Загружено ${data.count} артикулов`);
        // После загрузки кеша сканируем страницу
        scanPage();
      } else {
        console.error('[MarketPlacer Extension] Ошибка загрузки артикулов:', data?.error || 'Unknown error');
        setTimeout(loadArticles, 5000);
      }
    } catch (error) {
      console.error('[MarketPlacer Extension] Ошибка загрузки артикулов:', error);
      // Повторная попытка через 5 секунд
      setTimeout(loadArticles, 5000);
    }
  }

  /**
   * Парсинг текста в артикул и размер
   * OZON: 3035090018/658 -> article: 3035090018, size: 658
   * WB: 2013060166-1 -> article: 2013060166-1, size: null
   */
  function parseArticle(text) {
    if (!text || typeof text !== 'string') return null;

    text = text.trim();

    if (MARKETPLACE === 'ozon') {
      // OZON: формат артикул/размер
      if (!CONFIG.ARTICLE_PATTERN_OZON.test(text)) return null;

      const parts = text.split('/');
      if (parts.length !== 2) return null;

      const article = parts[0];
      const size = parts[1];

      if (!/^\d[\d-]*$/.test(article)) return null;

      return { article, size, full: text };
    } else if (MARKETPLACE === 'wb') {
      // WB: формат просто артикул (с возможным -суффиксом)
      if (!CONFIG.ARTICLE_PATTERN_WB.test(text)) return null;

      return { article: text, size: null, full: text };
    }

    return null;
  }

  /**
   * Проверка, есть ли артикул в базе
   */
  function isKnownArticle(article) {
    return articlesCache.has(article);
  }

  /**
   * Получение данных о товаре OZON (через background script)
   */
  async function getOzonProductInfo(article, size) {
    const cacheKey = `ozon:${article}/${size}`;

    // Проверяем кеш
    if (productDataCache.has(cacheKey)) {
      return productDataCache.get(cacheKey);
    }

    try {
      const data = await chrome.runtime.sendMessage({
        action: 'fetchProductInfo',
        article: article,
        size: size
      });

      if (data && data.success) {
        productDataCache.set(cacheKey, data);
        return data;
      } else {
        return { error: data?.error || 'Ошибка получения данных' };
      }
    } catch (error) {
      console.error('[MarketPlacer Extension] Ошибка запроса:', error);
      return { error: 'Ошибка соединения с сервером' };
    }
  }

  /**
   * Получение данных о товаре WB (через background script)
   */
  async function getWBProductInfo(article, size) {
    const cacheKey = `wb:${article}/${size}`;

    // Проверяем кеш
    if (productDataCache.has(cacheKey)) {
      return productDataCache.get(cacheKey);
    }

    try {
      const data = await chrome.runtime.sendMessage({
        action: 'fetchWBProductInfo',
        article: article,
        size: size
      });

      if (data && data.success) {
        productDataCache.set(cacheKey, data);
        return data;
      } else {
        return { error: data?.error || 'Ошибка получения данных' };
      }
    } catch (error) {
      console.error('[MarketPlacer Extension] Ошибка запроса:', error);
      return { error: 'Ошибка соединения с сервером' };
    }
  }

  /**
   * Получение данных о товаре (универсальная функция)
   */
  async function getProductInfo(article, size) {
    if (MARKETPLACE === 'ozon') {
      return getOzonProductInfo(article, size);
    } else if (MARKETPLACE === 'wb') {
      return getWBProductInfo(article, size);
    }
    return { error: 'Неизвестный маркетплейс' };
  }

  /**
   * Создание тултипа
   */
  function createTooltip() {
    if (tooltip) return tooltip;

    tooltip = document.createElement('div');
    tooltip.className = 'mp-tooltip';
    tooltip.style.display = 'none';
    document.body.appendChild(tooltip);

    return tooltip;
  }

  /**
   * Отображение тултипа с загрузкой
   */
  function showTooltipLoading(x, y) {
    const tip = createTooltip();
    tip.innerHTML = '<div class="mp-tooltip-loading">Загрузка...</div>';
    positionTooltip(tip, x, y);
    tip.style.display = 'block';
  }

  /**
   * Отображение тултипа с данными OZON
   */
  function showOzonTooltipData(data, x, y) {
    const tip = createTooltip();

    if (data.error) {
      tip.innerHTML = `<div class="mp-tooltip-error">${data.error}</div>`;
    } else {
      // Определяем класс для процента выкупа
      let percentClass = 'percent';
      if (data.buyout_percent >= 80) {
        percentClass += ' good';
      } else if (data.buyout_percent < 50) {
        percentClass += ' bad';
      }

      tip.innerHTML = `
        <div class="mp-tooltip-title">${data.article}/${data.size}</div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">Остаток:</span>
          <span class="mp-tooltip-value stock">${data.stock} шт</span>
        </div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">Заказов:</span>
          <span class="mp-tooltip-value orders">${data.orders_total}</span>
        </div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">Выкуплено:</span>
          <span class="mp-tooltip-value delivered">${data.delivered}</span>
        </div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">Отменено:</span>
          <span class="mp-tooltip-value cancelled">${data.cancelled}</span>
        </div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">% выкупа:</span>
          <span class="mp-tooltip-value ${percentClass}">${data.buyout_percent}%</span>
        </div>
        <div class="mp-tooltip-row">
          <span class="mp-tooltip-label">Доставляется:</span>
          <span class="mp-tooltip-value orders">${data.delivering || 0}</span>
        </div>
      `;
    }

    positionTooltip(tip, x, y);
    tip.style.display = 'block';
  }

  /**
   * Отображение тултипа с данными WB (табличный вид с мульти-токенами)
   */
  function showWBTooltipData(data, x, y) {
    const tip = createTooltip();

    if (data.error) {
      tip.innerHTML = `<div class="mp-tooltip-error">${data.error}</div>`;
    } else if (!data.tokens || data.tokens.length === 0) {
      tip.innerHTML = `<div class="mp-tooltip-error">Нет данных по токенам</div>`;
    } else {
      // Заголовок
      let html = `<div class="mp-tooltip-title">${data.article}${data.size ? '/' + data.size : ''}</div>`;

      // Таблица с токенами
      html += '<table class="mp-tooltip-table">';

      // Заголовки колонок
      html += '<tr class="mp-tooltip-header">';
      html += '<th></th>';
      data.tokens.forEach(token => {
        html += `<th>${token.token_name}</th>`;
      });
      html += '</tr>';

      // Строка: Остаток
      html += '<tr>';
      html += '<td class="mp-tooltip-label">Остаток</td>';
      data.tokens.forEach(token => {
        html += `<td class="mp-tooltip-value stock">${token.stock}</td>`;
      });
      html += '</tr>';

      // Строка: К клиенту
      html += '<tr>';
      html += '<td class="mp-tooltip-label">К клиенту</td>';
      data.tokens.forEach(token => {
        html += `<td class="mp-tooltip-value orders">${token.in_way_to_client}</td>`;
      });
      html += '</tr>';

      // Строка: Заказов
      html += '<tr>';
      html += '<td class="mp-tooltip-label">Заказов</td>';
      data.tokens.forEach(token => {
        html += `<td class="mp-tooltip-value orders">${token.orders_total}</td>`;
      });
      html += '</tr>';

      // Строка: Выкуплено
      html += '<tr>';
      html += '<td class="mp-tooltip-label">Выкуплено</td>';
      data.tokens.forEach(token => {
        html += `<td class="mp-tooltip-value delivered">${token.delivered}</td>`;
      });
      html += '</tr>';

      // Строка: Отменено
      html += '<tr>';
      html += '<td class="mp-tooltip-label">Отменено</td>';
      data.tokens.forEach(token => {
        html += `<td class="mp-tooltip-value cancelled">${token.cancelled}</td>`;
      });
      html += '</tr>';

      // Строка: % выкупа
      html += '<tr>';
      html += '<td class="mp-tooltip-label">% выкупа</td>';
      data.tokens.forEach(token => {
        let percentClass = 'percent';
        if (token.buyout_percent >= 80) {
          percentClass += ' good';
        } else if (token.buyout_percent < 50) {
          percentClass += ' bad';
        }
        html += `<td class="mp-tooltip-value ${percentClass}">${token.buyout_percent}%</td>`;
      });
      html += '</tr>';

      html += '</table>';
      tip.innerHTML = html;
    }

    positionTooltip(tip, x, y);
    tip.style.display = 'block';
  }

  /**
   * Отображение тултипа с данными (универсальная функция)
   */
  function showTooltipData(data, x, y) {
    if (MARKETPLACE === 'ozon') {
      showOzonTooltipData(data, x, y);
    } else if (MARKETPLACE === 'wb') {
      showWBTooltipData(data, x, y);
    }
  }

  /**
   * Позиционирование тултипа
   */
  function positionTooltip(tip, x, y) {
    const padding = 10;
    const rect = tip.getBoundingClientRect();

    // Проверяем, не выходит ли за правый край
    if (x + rect.width + padding > window.innerWidth) {
      x = window.innerWidth - rect.width - padding;
    }

    // Проверяем, не выходит ли за нижний край
    if (y + rect.height + padding > window.innerHeight) {
      y = y - rect.height - padding;
    }

    tip.style.left = `${x + padding}px`;
    tip.style.top = `${y + padding}px`;
  }

  /**
   * Скрытие тултипа
   */
  function hideTooltip() {
    if (tooltip) {
      tooltip.style.display = 'none';
    }
    if (hoverTimeout) {
      clearTimeout(hoverTimeout);
      hoverTimeout = null;
    }
    currentElement = null;
  }

  /**
   * Обработчик наведения на элемент
   */
  async function handleMouseEnter(event) {
    const element = event.target;
    const parsed = element._mpArticleData;

    if (!parsed) return;

    currentElement = element;

    // Показываем тултип с задержкой
    hoverTimeout = setTimeout(async () => {
      if (currentElement !== element) return;

      showTooltipLoading(event.clientX, event.clientY);

      const data = await getProductInfo(parsed.article, parsed.size);

      if (currentElement === element) {
        showTooltipData(data, event.clientX, event.clientY);
      }
    }, CONFIG.HOVER_DELAY);
  }

  /**
   * Обработчик ухода с элемента
   */
  function handleMouseLeave() {
    hideTooltip();
  }

  /**
   * Обработчик движения мыши (для обновления позиции)
   */
  function handleMouseMove(event) {
    if (tooltip && tooltip.style.display === 'block') {
      positionTooltip(tooltip, event.clientX, event.clientY);
    }
  }

  /**
   * Проверка и пометка элемента как артикула
   */
  function processTextNode(node) {
    const text = node.textContent.trim();
    const parsed = parseArticle(text);

    if (!parsed) return;
    if (!isKnownArticle(parsed.article)) return;

    // Находим родительский элемент
    const parent = node.parentElement;
    if (!parent) return;

    // Проверяем, не обработан ли уже
    if (parent._mpProcessed) return;

    // Помечаем элемент
    parent._mpProcessed = true;
    parent._mpArticleData = parsed;
    parent.classList.add('mp-article-highlight');

    // Добавляем обработчики
    parent.addEventListener('mouseenter', handleMouseEnter);
    parent.addEventListener('mouseleave', handleMouseLeave);
    parent.addEventListener('mousemove', handleMouseMove);
  }

  /**
   * Сканирование страницы на наличие артикулов
   */
  function scanPage() {
    if (!cacheLoaded) return;

    // Получаем все текстовые узлы
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function(node) {
          // Пропускаем скрипты, стили и уже обработанные
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          if (parent._mpProcessed) return NodeFilter.FILTER_REJECT;

          const tag = parent.tagName.toLowerCase();
          if (tag === 'script' || tag === 'style' || tag === 'noscript') {
            return NodeFilter.FILTER_REJECT;
          }

          // Проверяем, похож ли текст на артикул
          const text = node.textContent.trim();
          const pattern = MARKETPLACE === 'ozon' ? CONFIG.ARTICLE_PATTERN_OZON : CONFIG.ARTICLE_PATTERN_WB;
          if (pattern.test(text)) {
            return NodeFilter.FILTER_ACCEPT;
          }

          return NodeFilter.FILTER_REJECT;
        }
      }
    );

    const nodesToProcess = [];
    while (walker.nextNode()) {
      nodesToProcess.push(walker.currentNode);
    }

    nodesToProcess.forEach(processTextNode);
  }

  /**
   * Наблюдатель за изменениями DOM
   */
  function setupMutationObserver() {
    const observer = new MutationObserver((mutations) => {
      let shouldScan = false;

      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          shouldScan = true;
          break;
        }
      }

      if (shouldScan) {
        // Debounce сканирования
        clearTimeout(window._mpScanTimeout);
        window._mpScanTimeout = setTimeout(scanPage, 500);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  /**
   * Инициализация расширения
   */
  function init() {
    console.log(`[MarketPlacer Extension] Инициализация на ${MARKETPLACE.toUpperCase()}...`);

    // Загружаем список артикулов
    loadArticles();

    // Настраиваем наблюдатель за DOM
    setupMutationObserver();

    // Периодическое сканирование (для динамического контента)
    setInterval(scanPage, CONFIG.SCAN_INTERVAL);

    console.log('[MarketPlacer Extension] Готово');
  }

  // Запуск
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
