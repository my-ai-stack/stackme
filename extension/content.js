/**
 * Stackme Content Script
 * Intercepts prompts on AI platforms, injects context from Stackme memory.
 */

(function () {
  'use strict';

  const STACKME_STORAGE_KEY = 'stackme_context';
  const INJECTED_CLASS = 'stackme-injected';
  const CONTEXT_PREFIX = '[Stackme Context]';

  // Detect which AI platform we're on
  function detectPlatform() {
    const host = window.location.hostname;
    if (host.includes('openai.com')) return 'chatgpt';
    if (host.includes('claude.ai')) return 'claude';
    if (host.includes('copilot')) return 'copilot';
    if (host.includes('gemini')) return 'gemini';
    return 'unknown';
  }

  // Find the textarea / input on the current platform
  function findInputBox(platform) {
    if (platform === 'chatgpt') {
      return document.querySelector('textarea[data-id="root"]') ||
             document.querySelector('#prompt-textarea') ||
             document.querySelector('.flex.flex-1 .textarea-wrapper textarea') ||
             document.querySelector('textarea');
    }
    if (platform === 'claude') {
      return document.querySelector('textarea[placeholder*="message"]') ||
             document.querySelector('textarea') ||
             document.querySelector('[data-placeholder]');
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

  // Get stored context from chrome.storage
  function getStoredContext() {
    return new Promise((resolve) => {
      if (typeof chrome === 'undefined' || !chrome.storage) {
        resolve(null);
        return;
      }
      chrome.storage.local.get([STACKME_STORAGE_KEY], (result) => {
        resolve(result[STACKME_STORAGE_KEY] || null);
      });
    });
  }

  // Inject context into the input box
  async function injectContext(inputBox) {
    if (!inputBox || inputBox.classList.contains(INJECTED_CLASS)) return;
    inputBox.classList.add(INJECTED_CLASS);

    const context = await getStoredContext();
    if (!context) return;

    const existingValue = inputBox.value || inputBox.innerText || '';
    if (existingValue.includes(CONTEXT_PREFIX)) return;

    const enriched = `${CONTEXT_PREFIX} ${context}\n\n${existingValue}`;

    // Set value and trigger input event so the AI UI picks it up
    inputBox.value = enriched;
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
    toast.innerHTML = `🧠 Stackme context loaded: <span style="opacity:0.7">${context.slice(0, 80)}...</span>`;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #1a1a2e;
      border: 1px solid #a855f7;
      color: #e8e8f0;
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 0.8rem;
      z-index: 99999;
      max-width: 320px;
      box-shadow: 0 4px 20px rgba(168,85,247,0.2);
      font-family: system-ui, sans-serif;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // Observe the input box for when it becomes active
  let observer = null;
  function startObserver(platform) {
    const platformInputs = {
      chatgpt: 'textarea[data-id="root"]',
      claude: 'textarea',
      copilot: '#userInput',
      gemini: 'textarea',
    };

    const selector = platformInputs[platform] || 'textarea';

    observer = new MutationObserver(() => {
      const inputBox = findInputBox(platform);
      if (inputBox && !inputBox.classList.contains(INJECTED_CLASS)) {
        // On focus, try to inject
        inputBox.addEventListener('focus', () => injectContext(inputBox), { once: true });
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Also try immediately
    const inputBox = findInputBox(platform);
    if (inputBox) {
      inputBox.addEventListener('focus', () => injectContext(inputBox), { once: true });
    }
  }

  // Main
  const platform = detectPlatform();
  if (platform !== 'unknown') {
    console.log(`[Stackme] Active on ${platform}`);
    startObserver(platform);

    // When user submits, also save their prompt to memory
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        const inputBox = findInputBox(platform);
        if (inputBox && inputBox.value) {
          // Save the user's prompt to chrome storage
          const prompt = inputBox.value.replace(`[Stackme Context]`, '').trim();
          if (typeof chrome !== 'undefined' && chrome.storage) {
            chrome.storage.local.get([STACKME_STORAGE_KEY], (result) => {
              const existing = result[STACKME_STORAGE_KEY] || '';
              const updated = existing
                ? `${existing}\nUser prompt: ${prompt.slice(0, 200)}`
                : `User prompt: ${prompt.slice(0, 200)}`;
              // Keep last 5 prompts
              const lines = updated.split('\n').slice(-10);
              chrome.storage.local.set({ [STACKME_STORAGE_KEY]: lines.join('\n') });
            });
          }
        }
      }
    });
  }
})();
