/**
 * Background Service Worker
 * Выполняет HTTP запросы к API (обходит mixed content блокировку)
 */

const API_BASE = 'http://192.168.0.66:5000/api/extension';

// Обработка сообщений от content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fetchArticles') {
    fetch(`${API_BASE}/articles`)
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Указываем, что ответ будет асинхронным
  }

  if (request.action === 'fetchProductInfo') {
    const { article, size } = request;
    const url = `${API_BASE}/product-info?article=${encodeURIComponent(article)}&size=${encodeURIComponent(size || '')}`;

    fetch(url)
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'fetchWBProductInfo') {
    const { article, size } = request;
    const url = `${API_BASE}/wb/product-info?article=${encodeURIComponent(article)}&size=${encodeURIComponent(size || '')}`;

    fetch(url)
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

console.log('[MarketPlacer Extension] Background service worker started');
