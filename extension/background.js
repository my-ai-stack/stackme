/**
 * Stackme Background Service Worker
 * Handles messages between content script and storage.
 */

const STACKME_STORAGE_KEY = 'stackme_context';

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_CONTEXT') {
    chrome.storage.local.get([STACKME_STORAGE_KEY], (result) => {
      sendResponse({ context: result[STACKME_STORAGE_KEY] || null });
    });
    return true;
  }

  if (message.type === 'SET_CONTEXT') {
    chrome.storage.local.set({ [STACKME_STORAGE_KEY]: message.context }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === 'ADD_FACT') {
    chrome.storage.local.get([STACKME_STORAGE_KEY], (result) => {
      const existing = result[STACKME_STORAGE_KEY] || '';
      const newFact = `Fact: ${message.fact}`;
      const updated = existing
        ? `${existing}\n${newFact}`
        : newFact;
      chrome.storage.local.set({ [STACKME_STORAGE_KEY]: updated }, () => {
        sendResponse({ success: true });
      });
    });
    return true;
  }

  if (message.type === 'GET_MEMORY_COUNT') {
    chrome.storage.local.get([STACKME_STORAGE_KEY], (result) => {
      const text = result[STACKME_STORAGE_KEY] || '';
      const count = text.split('\n').filter(l => l.trim()).length;
      sendResponse({ count });
    });
    return true;
  }
});

// Badge on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.action.setBadgeText({ text: 'me' });
  chrome.action.setBadgeBackgroundColor({ color: '#a855f7' });
  console.log('[Stackme] Extension installed');
});
