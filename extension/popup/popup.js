/**
 * Stackme Popup UI Logic
 */

const STORAGE_KEY = 'stackme_context';

async function loadFacts() {
  const result = await chrome.storage.local.get([STORAGE_KEY]);
  const text = result[STORAGE_KEY] || '';
  const lines = text.split('\n').filter(l => l.trim());
  return lines;
}

async function saveFacts(lines) {
  await chrome.storage.local.set({ [STORAGE_KEY]: lines.join('\n') });
}

async function refreshUI() {
  const facts = await loadFacts();
  const count = facts.length;
  document.getElementById('count').textContent = count;

  const list = document.getElementById('factsList');
  if (facts.length === 0) {
    list.innerHTML = '<div class="empty">No memories yet. Add your first fact above.</div>';
  } else {
    list.innerHTML = facts.map(f =>
      `<div class="fact-item"><span class="dot">●</span>${escapeHtml(f)}</div>`
    ).join('');
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

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

async function clearAll() {
  if (!confirm('Clear all Stackme memories?')) return;
  await chrome.storage.local.remove([STORAGE_KEY]);
  await refreshUI();
}

document.getElementById('addBtn').addEventListener('click', addFact);
document.getElementById('factInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') addFact();
});
document.getElementById('clearBtn').addEventListener('click', clearAll);

// Init
refreshUI();
