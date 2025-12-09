/**
 * OZON Product Info Extension
 * Показывает информацию о товарах из базы при наведении на артикул
 */

(function() {
  'use strict';

  // Конфигурация
  const CONFIG = {
    // Используем HTTP - браузер может блокировать из-за mixed content
    // Если не работает, нужно настроить HTTPS на сервере
    API_BASE: 'http://192.168.0.44:5000/api/extension',
    // Паттерн артикула: цифры (возможно с дефисами)/что-угодно
    // Примеры: 3035090018/658, 2089090018-14/11, 3009030003/M
    ARTICLE_PATTERN: /^[\d-]+\/[\w\d.,]+$/,
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
        console.log(`[OZON Extension] Загружено ${data.count} артикулов`);
        // После загрузки кеша сканируем страницу
        scanPage();
      } else {
        console.error('[OZON Extension] Ошибка загрузки артикулов:', data?.error || 'Unknown error');
        setTimeout(loadArticles, 5000);
      }
    } catch (error) {
      console.error('[OZON Extension] Ошибка загрузки артикулов:', error);
      // Повторная попытка через 5 секунд
      setTimeout(loadArticles, 5000);
    }
  }

  /**
   * Парсинг текста в артикул и размер
   * Примеры:
   *   3035090018/658 -> article: 3035090018, size: 658
   *   2089090018-14/11 -> article: 2089090018-14, size: 11
   *   3009030003/M -> article: 3009030003, size: M
   */
  function parseArticle(text) {
    if (!text || typeof text !== 'string') return null;

    text = text.trim();

    // Проверяем паттерн: цифры (возможно с дефисами)/что-то
    if (!CONFIG.ARTICLE_PATTERN.test(text)) return null;

    const parts = text.split('/');
    if (parts.length !== 2) return null;

    const article = parts[0];  // Артикул полностью, включая дефис (2089090018-14)
    const size = parts[1];

    // Артикул должен содержать только цифры и дефисы, и начинаться с цифры
    if (!/^\d[\d-]*$/.test(article)) return null;

    return { article, size, full: text };
  }

  /**
   * Проверка, есть ли артикул в базе
   */
  function isKnownArticle(article) {
    return articlesCache.has(article);
  }

  /**
   * Получение данных о товаре (через background script)
   */
  async function getProductInfo(article, size) {
    const cacheKey = `${article}/${size}`;

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
      console.error('[OZON Extension] Ошибка запроса:', error);
      return { error: 'Ошибка соединения с сервером' };
    }
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
   * Отображение тултипа с данными
   */
  function showTooltipData(data, x, y) {
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
          if (CONFIG.ARTICLE_PATTERN.test(text)) {
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
    console.log('[OZON Extension] Инициализация...');

    // Загружаем список артикулов
    loadArticles();

    // Настраиваем наблюдатель за DOM
    setupMutationObserver();

    // Периодическое сканирование (для динамического контента)
    setInterval(scanPage, CONFIG.SCAN_INTERVAL);

    console.log('[OZON Extension] Готово');
  }

  // Запуск
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
