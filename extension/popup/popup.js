/**
 * Stackme Popup UI Logic
 */

const STORAGE_KEY = 'stackme_context';
const ENABLED_KEY = 'stackme_injection_enabled';

// Load facts from storage
async function loadFacts() {
  const result = await chrome.storage.local.get([STORAGE_KEY]);
  const text = result[STORAGE_KEY] || '';
  const lines = text.split('\n').filter(l => l.trim());
  return lines;
}

// Save facts to storage
async function saveFacts(lines) {
  await chrome.storage.local.set({ [STORAGE_KEY]: lines.join('\n') });
}

// Load enabled state
async function loadEnabled() {
  const result = await chrome.storage.local.get([ENABLED_KEY]);
  // Default to enabled
  return result[ENABLED_KEY] !== false;
}

// Save enabled state
async function saveEnabled(enabled) {
  await chrome.storage.local.set({ [ENABLED_KEY]: enabled });
}

// Refresh the UI
async function refreshUI() {
  const facts = await loadFacts();
  const count = facts.length;
  const enabled = await loadEnabled();

  // Update status
  document.getElementById('count').textContent = count;

  // Update toggle
  const toggle = document.getElementById('injectToggle');
  toggle.checked = enabled;

  // Update facts list
  const list = document.getElementById('factsList');
  if (facts.length === 0) {
    list.innerHTML = '<div class="empty">No memories yet. Add your first fact above.</div>';
  } else {
    list.innerHTML = facts.map((f, i) => `
      <div class="fact-item">
        <span class="dot">●</span>
        <span class="fact-content">${escapeHtml(f)}</span>
        <button class="delete-btn" data-index="${i}" title="Delete">×</button>
      </div>
    `).join('');

    // Add delete handlers
    list.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const index = parseInt(e.target.dataset.index);
        await deleteFact(index);
      });
    });
  }
}

// Escape HTML for display
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Add a new fact
async function addFact() {
  const input = document.getElementById('factInput');
  const fact = input.value.trim();
  if (!fact) return;

  const facts = await loadFacts();
  facts.push(fact);
  await saveFacts(facts);
  input.value = '';
  await refreshUI();
}

// Delete a fact by index
async function deleteFact(index) {
  const facts = await loadFacts();
  if (index >= 0 && index < facts.length) {
    facts.splice(index, 1);
    await saveFacts(facts);
    await refreshUI();
  }
}

// Clear all facts
async function clearAll() {
  if (!confirm('Clear all Stackme memories?')) return;
  await chrome.storage.local.remove([STORAGE_KEY]);
  await refreshUI();
}

// Inject context now (manual trigger)
async function injectNow() {
  // Get the active tab and send message to content script
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.id) {
    try {
      await chrome.tabs.sendMessage(tab.id, { type: 'INJECT_CONTEXT' });
      showToast('Context injected!');
    } catch (e) {
      showToast('Cannot inject on this page');
    }
  }
}

// Show temporary toast
function showToast(message) {
  const existing = document.getElementById('stackme-toast-popup');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'stackme-toast-popup';
  toast.textContent = message;
  toast.style.cssText = `
    position: absolute;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: #a855f7;
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.8rem;
    z-index: 100;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Add button
  document.getElementById('addBtn').addEventListener('click', addFact);

  // Enter key in input
  document.getElementById('factInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') addFact();
  });

  // Toggle
  document.getElementById('injectToggle').addEventListener('change', async (e) => {
    await saveEnabled(e.target.checked);
  });

  // Clear button
  document.getElementById('clearBtn').addEventListener('click', clearAll);

  // Inject now button
  const injectBtn = document.getElementById('injectNowBtn');
  if (injectBtn) {
    injectBtn.addEventListener('click', injectNow);
  }

  // Initial load
  refreshUI();
});