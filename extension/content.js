/**
 * Stackme Content Script
 * Intercepts prompts on AI platforms, injects context from Stackme memory.
 */

(function () {
  'use strict';

  const STACKME_CONTEXT_KEY = 'stackme_context';
  const STACKME_ENABLED_KEY = 'stackme_injection_enabled';
  const INJECTED_CLASS = 'stackme-injected';
  const CONTEXT_PREFIX = '[Stackme Context]';
  let injectedThisFocus = false;

  // Detect which AI platform we're on
  function detectPlatform() {
    const host = window.location.hostname;
    if (host.includes('chat.openai.com')) return 'chatgpt';
    if (host.includes('claude.ai')) return 'claude';
    if (host.includes('copilot.microsoft.com') || host.includes('copilot.com')) return 'copilot';
    if (host.includes('gemini.google.com')) return 'gemini';
    if (host.includes('chatgpt.com')) return 'chatgpt';
    return 'unknown';
  }

  // Find the textarea / input on the current platform
  function findInputBox(platform) {
    if (platform === 'chatgpt') {
      return document.querySelector('textarea[data-id="root"]') ||
             document.querySelector('#prompt-textarea') ||
             document.querySelector('textarea[placeholder*="message"]') ||
             document.querySelector('textarea');
    }
    if (platform === 'claude') {
      return document.querySelector('textarea[placeholder*="message"]') ||
             document.querySelector('textarea') ||
             document.querySelector('[contenteditable="true"]');
    }
    if (platform === 'copilot') {
      return document.querySelector('#userInput') ||
             document.querySelector('textarea#searchInput') ||
             document.querySelector('textarea');
    }
    if (platform === 'gemini') {
      return document.querySelector('textarea[name="query"]') ||
             document.querySelector('textarea') ||
             document.querySelector('[contenteditable="true"]');
    }
    return document.querySelector('textarea');
  }

  // Check if injection is enabled
  function isInjectionEnabled() {
    return new Promise((resolve) => {
      if (typeof chrome === 'undefined' || !chrome.storage) {
        resolve(true);
        return;
      }
      chrome.storage.local.get([STACKME_ENABLED_KEY], (result) => {
        // Default to enabled if not set
        resolve(result[STACKME_ENABLED_KEY] !== false);
      });
    });
  }

  // Get stored context from chrome.storage
  function getStoredContext() {
    return new Promise((resolve) => {
      if (typeof chrome === 'undefined' || !chrome.storage) {
        resolve(null);
        return;
      }
      chrome.storage.local.get([STACKME_CONTEXT_KEY], (result) => {
        resolve(result[STACKME_CONTEXT_KEY] || null);
      });
    });
  }

  // Check if context was already injected this focus session
  function wasInjectedThisFocus() {
    return injectedThisFocus;
  }

  function setInjectedThisFocus(value) {
    injectedThisFocus = value;
  }

  // Inject context into the input box
  async function injectContext(inputBox, force = false) {
    if (!inputBox) return;

    const enabled = await isInjectionEnabled();
    if (!enabled && !force) {
      console.log('[Stackme] Injection disabled');
      return;
    }

    // Check if already injected this focus
    if (wasInjectedThisFocus() && !force) {
      return;
    }

    // Check if input already has our prefix
    const existingValue = inputBox.value || inputBox.innerText || '';
    if (existingValue.includes(CONTEXT_PREFIX)) {
      setInjectedThisFocus(true);
      return;
    }

    const context = await getStoredContext();
    if (!context) {
      console.log('[Stackme] No context stored');
      return;
    }

    // Mark as injected
    setInjectedThisFocus(true);
    inputBox.classList.add(INJECTED_CLASS);

    // Prepend context to the input
    const enriched = `${CONTEXT_PREFIX} ${context}\n\n${existingValue}`;

    // Set value and trigger input event so the AI UI picks it up
    if (inputBox.value !== undefined) {
      inputBox.value = enriched;
    } else if (inputBox.innerText !== undefined) {
      inputBox.innerText = enriched;
    }

    inputBox.dispatchEvent(new Event('input', { bubbles: true }));
    inputBox.dispatchEvent(new Event('change', { bubbles: true }));

    // Visual indicator
    showContextIndicator(context);
  }

  // Show a small toast that context was injected
  function showContextIndicator(context) {
    const existing = document.getElementById('stackme-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'stackme-toast';
    toast.innerHTML = `🧠 Stackme context loaded: <span style="opacity:0.7">${context.slice(0, 60)}...</span>`;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #1a1a2e;
      border: 1px solid #a855f7;
      color: #e8e8f0;
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 0.85rem;
      z-index: 99999;
      max-width: 350px;
      box-shadow: 0 4px 20px rgba(168,85,247,0.3);
      font-family: system-ui, -apple-system, sans-serif;
      animation: stackme-slide-in 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Add keyboard shortcut listener (Ctrl+Shift+M or Cmd+Shift+M)
  function setupKeyboardShortcut(platform) {
    document.addEventListener('keydown', async (e) => {
      // Check for Ctrl+Shift+M or Cmd+Shift+M
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'm') {
        e.preventDefault();
        const inputBox = findInputBox(platform);
        if (inputBox) {
          // Reset injection flag to allow re-injection
          setInjectedThisFocus(false);
          await injectContext(inputBox, true);
        }
      }
    });
  }

  // Observe for input box appearance
  let observer = null;
  function startObserver(platform) {
    // Try immediately first
    setTimeout(() => {
      const inputBox = findInputBox(platform);
      if (inputBox) {
        setupInputBox(inputBox, platform);
      }
    }, 500);

    // Also observe for dynamic content
    observer = new MutationObserver(() => {
      const inputBox = findInputBox(platform);
      if (inputBox && !inputBox.classList.contains('stackme-listener-attached')) {
        setupInputBox(inputBox, platform);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true, once: true });
  }

  // Setup listeners on input box
  function setupInputBox(inputBox, platform) {
    if (!inputBox || inputBox.classList.contains('stackme-listener-attached')) return;

    inputBox.classList.add('stackme-listener-attached');

    // Inject on focus (only once per focus)
    inputBox.addEventListener('focus', async () => {
      const enabled = await isInjectionEnabled();
      if (enabled) {
        await injectContext(inputBox);
      }
    }, { once: false });

    // Reset injection flag when user clears the input
    inputBox.addEventListener('input', () => {
      const val = inputBox.value || inputBox.innerText || '';
      if (!val.includes(CONTEXT_PREFIX)) {
        setInjectedThisFocus(false);
      }
    });

    // Keyboard shortcut
    setupKeyboardShortcut(platform);
  }

  // Main
  const platform = detectPlatform();
  if (platform !== 'unknown') {
    console.log(`[Stackme] Active on ${platform}`);
    startObserver(platform);

    // Listen for messages from popup/background
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'INJECT_CONTEXT') {
          const inputBox = findInputBox(platform);
          if (inputBox) {
            setInjectedThisFocus(false);
            injectContext(inputBox, true).then(() => sendResponse({ success: true }));
            return true;
          }
        }
        if (message.type === 'GET_STATUS') {
          sendResponse({ platform, hasContext: true });
        }
      });
    }
  }
})();