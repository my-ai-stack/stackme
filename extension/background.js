/**
 * Stackme Background Service Worker
 * Handles messages between content script and storage.
 */

const STACKME_STORAGE_KEY = 'stackme_context';
const STACKME_ENABLED_KEY = 'stackme_injection_enabled';

// Handle messages from content script or popup
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

  if (message.type === 'GET_ENABLED') {
    chrome.storage.local.get([STACKME_ENABLED_KEY], (result) => {
      sendResponse({ enabled: result[STACKME_ENABLED_KEY] !== false });
    });
    return true;
  }

  if (message.type === 'SET_ENABLED') {
    chrome.storage.local.set({ [STACKME_ENABLED_KEY]: message.enabled }, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  // Forward inject command to content script
  if (message.type === 'INJECT_CONTEXT') {
    // This is handled by the popup directly sending to content script
    sendResponse({ forwarded: true });
    return true;
  }
});

// Badge on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.action.setBadgeText({ text: 'me' });
  chrome.action.setBadgeBackgroundColor({ color: '#a855f7' });
  console.log('[Stackme] Extension installed');

  // Set default values
  chrome.storage.local.set({
    [STACKME_ENABLED_KEY]: true
  });
});

// Optional: Tab update listener for badge
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const supportedDomains = ['chat.openai.com', 'claude.ai', 'copilot.microsoft.com', 'gemini.google.com', 'chatgpt.com'];
    const isSupported = supportedDomains.some(domain => tab.url.includes(domain));

    if (isSupported) {
      chrome.action.setBadgeText({ text: 'me', tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: '#a855f7', tabId: tabId });
    } else {
      chrome.action.setBadgeText({ text: '', tabId: tabId });
    }
  }
});