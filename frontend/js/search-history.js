/* ═══════════════════════════════════════════════
   search-history.js — Search history sidebar tab
   Stores queries with timestamps in localStorage
═══════════════════════════════════════════════ */

const HISTORY_STORAGE_KEY = 'alilm-search-history';
const HISTORY_MAX_ITEMS = 50;

let historySidebarVisible = false;

/* ── Data structure ── */
function getSearchHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveSearchHistory(history) {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (e) { /* ignore */ }
}

function addSearchEntry(query, answerPreview) {
  const history = getSearchHistory();
  const entry = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    query: query.slice(0, 200),
    answerPreview: (answerPreview || '').slice(0, 120),
    timestamp: Date.now(),
    date: new Date().toISOString(),
  };
  history.unshift(entry);
  if (history.length > HISTORY_MAX_ITEMS) history.pop();
  saveSearchHistory(history);
  renderHistorySidebar();
}

function clearSearchHistory() {
  if (!confirm('Clear all search history?')) return;
  saveSearchHistory([]);
  renderHistorySidebar();
  showToast('Search history cleared');
}

/* ── Format timestamps ── */
function formatTimestamp(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/* ── Render history in sidebar ── */
function renderHistorySidebar() {
  const container = document.getElementById('sidebarHistory');
  const empty = document.getElementById('historyEmpty');
  const countEl = document.getElementById('historyCount');
  if (!container) return;

  const history = getSearchHistory();

  if (countEl) countEl.textContent = history.length;

  // Clear existing items
  container.querySelectorAll('.history-item').forEach(el => el.remove());

  if (!history.length) {
    if (empty) empty.classList.remove('hidden');
    return;
  }

  if (empty) empty.classList.add('hidden');

  history.forEach(entry => {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.dataset.query = entry.query;

    item.innerHTML = `
      <div class="history-query">${escapeHtml(entry.query)}</div>
      <div class="history-meta">
        <span class="history-time">${formatTimestamp(entry.timestamp)}</span>
        ${entry.answerPreview ? `<span class="history-preview">${escapeHtml(entry.answerPreview)}</span>` : ''}
      </div>
    `;

    item.addEventListener('click', () => {
      // Set the query in the input and send it
      const input = document.getElementById('queryInput');
      if (input) {
        input.value = entry.query;
        autoResize(input);
        input.focus();
        sendQuery();
      }
    });

    container.appendChild(item);
  });
}

/* ── Toggle sidebar tabs ── */
function toggleSidebarTab(tab) {
  const citationsTab = document.getElementById('citationsList');
  const historyTab = document.getElementById('sidebarHistory');
  const citationsBtn = document.getElementById('tabCitationsBtn');
  const historyBtn = document.getElementById('tabHistoryBtn');

  const clearBtn = document.getElementById('clearHistoryBtn');
  if (tab === 'history') {
    citationsTab.style.display = 'none';
    historyTab.style.display = 'flex';
    if (citationsBtn) citationsBtn.classList.remove('active');
    if (historyBtn) historyBtn.classList.add('active');
    historySidebarVisible = true;
    renderHistorySidebar();
    if (clearBtn) clearBtn.style.display = '';
  } else {
    citationsTab.style.display = 'flex';
    historyTab.style.display = 'none';
    if (citationsBtn) citationsBtn.classList.add('active');
    if (historyBtn) historyBtn.classList.remove('active');
    historySidebarVisible = false;
    if (clearBtn) clearBtn.style.display = 'none';
  }
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  // Render history on load if tab is active
  if (document.getElementById('sidebarHistory')) {
    renderHistorySidebar();
  }
});
