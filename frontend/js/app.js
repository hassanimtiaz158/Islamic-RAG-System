/* ═══════════════════════════════════════════════
   app.js — Main application logic
   WebSocket streaming + REST fallback + UI state
═══════════════════════════════════════════════ */

/* ── Config ── */
// When deployed (Vercel + Render), API_BASE is empty so requests use relative paths
// which get proxied by Vercel rewrites to the backend. When running locally, FastAPI serves both.
const API_BASE   = (window.__API_BASE__) || '';
const WS_URL     = API_BASE
  ? API_BASE.replace(/^http/, 'ws') + '/ws/ask'
  : ((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/ask');

// In production (Vercel), WebSocket to external Render backend may be blocked.
// Detect if we're on Vercel and skip WebSocket, use REST only.
const IS_VERCEL = !API_BASE && (window.location.hostname.includes('.vercel.app') || window.location.hostname.includes('vercel.app'));

/* ── App state ── */
let currentLang         = 'en';
let isLoading           = false;
let ws                  = null;
let reconnectTimer      = null;
let _streamBubble       = null;

/* ═══════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  restoreTheme();
  restoreChatHistory();
  connectWebSocket();

  document.getElementById('queryInput').addEventListener('input', function () {
    autoResize(this);
  });
});

/* ═══════════════════════════════════════════════
   DARK / LIGHT MODE
═══════════════════════════════════════════════ */
const themeToggle = document.getElementById('themeToggle');

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('alilm-theme', next);
  updateThemeIcons(next);
});

function restoreTheme() {
  const saved = localStorage.getItem('alilm-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcons(saved);
}

function updateThemeIcons(theme) {
  const sun = themeToggle.querySelector('.theme-icon-sun');
  const moon = themeToggle.querySelector('.theme-icon-moon');
  if (theme === 'dark') {
    sun.style.display = 'none';
    moon.style.display = 'block';
  } else {
    sun.style.display = 'block';
    moon.style.display = 'none';
  }
}

/* ═══════════════════════════════════════════════
   CHAT HISTORY (localStorage)
═══════════════════════════════════════════════ */
const STORAGE_KEY = 'alilm-chat-history';

function saveChatHistory() {
  const msgs = document.querySelectorAll('#chatMessages .msg');
  const history = [];
  msgs.forEach(msg => {
    const bubble = msg.querySelector('.bubble');
    if (!bubble) return;
    const isUser = msg.classList.contains('msg-user');
    const text = bubble.textContent || '';
    if (text.trim()) {
      history.push({ role: isUser ? 'user' : 'assistant', content: text });
    }
  });
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (e) { /* ignore */ }
}

function restoreChatHistory() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    const history = JSON.parse(saved);
    if (!history.length) return;

    // Remove welcome screen
    hideWelcome();

    history.forEach(msg => {
      if (msg.role === 'user') {
        addUserBubble(msg.content);
      } else {
        const citations = extractCitations(msg.content);
        addAssistantBubble(msg.content, citations, citations.length > 0);
        renderCitationCards(citations);
      }
    });
  } catch (e) { /* ignore */ }
}

function clearChat() {
  if (!confirm('Clear all chat messages?')) return;
  const msgs = document.getElementById('chatMessages');
  // Remove all message nodes (keep welcome)
  msgs.querySelectorAll('.msg').forEach(el => el.remove());
  // Also clear citations
  const list = document.getElementById('citationsList');
  list.querySelectorAll('.citation-card').forEach(el => el.remove());
  document.getElementById('citationCount').textContent = '0';
  document.getElementById('citationsEmpty').classList.remove('hidden');
  // Show welcome again
  document.getElementById('welcomeScreen').classList.remove('hidden');
  localStorage.removeItem(STORAGE_KEY);
  showToast('Chat cleared');
}

/* ═══════════════════════════════════════════════
   WEBSOCKET (streaming)
═══════════════════════════════════════════════ */
function connectWebSocket() {
  // Skip WebSocket on Vercel — external WS connections are blocked
  if (IS_VERCEL) {
    setStatus('online', 'Connected to backend');
    return;
  }

  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }

  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setStatus('online', 'Connected to backend');
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    ws.onmessage = ({ data }) => {
      try {
        const msg = JSON.parse(data);

        if (msg.type === 'token') {
          appendStreamToken(msg.content);
        } else if (msg.type === 'done') {
          finalizeStreamResponse(msg);
        } else if (msg.type === 'error') {
          handleStreamError(msg.message || 'Backend error');
        }
      } catch (e) {
        console.warn('[WS] Failed to parse message:', e);
      }
    };

    ws.onerror = () => {
      console.warn('[WS] WebSocket error — will use REST fallback');
      setStatus('warning', 'WebSocket failed, using REST');
      ws = null;
    };

    ws.onclose = () => {
      console.log('[WS] Connection closed');
      ws = null;
      scheduleReconnect();
    };
  } catch (e) {
    ws = null;
    setStatus('warning', 'WebSocket unavailable, using REST');
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 10000);
}

function handleStreamError(message) {
  removeTypingIndicator();
  addAssistantBubble(
    `⚠️ ${message}\n\nPlease try rephrasing your question or select different sources.`,
    [],
    false
  );
  isLoading = false;
  if (_streamBubble) _streamBubble = null;
}

/* Streaming helpers */
function appendStreamToken(token) {
  if (!_streamBubble) {
    removeTypingIndicator();
    _streamBubble = createAssistantBubble();
  }
  const content = _streamBubble.querySelector('.bubble-content');
  if (content) {
    content.textContent += token;
    scrollBottom();
  }
}

function finalizeStreamResponse(msg) {
  if (_streamBubble) {
    const content = _streamBubble.querySelector('.bubble-content');
    if (content) {
      const text = content.textContent;

      // Replace plain text with highlighted citations
      content.innerHTML = highlightCitations(escapeHtml(text));

      const citations = msg.citation_cards
        ? msg.citation_cards.map(c => ({
            type: (c.source || 'hadith').toLowerCase(),
            raw: c.raw || c.reference || '',
            ref: c.reference || '',
            url: c.url || ''
          }))
        : extractCitations(text);

      // Verse display
      const verseEl = _streamBubble.querySelector('.verse-slot');
      if (verseEl) verseEl.innerHTML = buildVerseDisplay(citations);

      // Badge
      const badge = _streamBubble.querySelector('.cite-badge');
      if (badge) {
        const valid = citations.length > 0;
        badge.className = `cite-badge ${valid ? 'valid' : 'invalid'}`;
        badge.innerHTML = `<span></span>${valid ? `Cited — ${citations.length} source${citations.length !== 1 ? 's' : ''}` : 'No citations found — using general knowledge'}`;
      }

      renderCitationCards(citations);
      addMsgActions(_streamBubble);
      saveChatHistory();
    }
    _streamBubble = null;
  }

  isLoading = false;
  scrollBottom();
}

/* ═══════════════════════════════════════════════
   SEND QUERY
═══════════════════════════════════════════════ */
async function sendQuery() {
  if (isLoading) return;

  const input = document.getElementById('queryInput');
  const query = input.value.trim();
  if (!query) return;

  isLoading = true;
  input.value = '';
  input.style.height = 'auto';

  hideWelcome();
  addUserBubble(query);
  addTypingIndicator();

  const sources = getSelectedSources();

  // ── Try WebSocket first (skip on Vercel — WS to external backend blocked) ──
  if (!IS_VERCEL && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      query,
      language: currentLang,
      sources,
    }));
    return; // response handled by ws.onmessage
  }

  // ── REST fallback ──
  try {
    setStatus('warning', 'Querying backend via REST…');
    const res = await fetch(`${API_BASE}/api/ask`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, language: currentLang, sources }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data     = await res.json();
    const answer   = data.answer || data.response || '';
    const citCards = data.citation_cards || [];

    const citations = citCards.length
      ? citCards.map(c => ({
          type: (c.source || 'hadith').toLowerCase(),
          raw: c.raw || c.reference || '',
          ref: c.reference || '',
          url: c.url || ''
        }))
      : extractCitations(answer);

    removeTypingIndicator();
    addAssistantBubble(answer, citations, citations.length > 0);
    renderCitationCards(citations);
    setStatus('online', 'Connected to backend');

  } catch (err) {
    console.warn('[REST] Backend error:', err.message);
    setStatus('warning', 'Backend unavailable — using local knowledge');

    const demo      = getDemoAnswer(query);
    const citations = extractCitations(demo);
    removeTypingIndicator();
    addAssistantBubble(demo, citations, true);
    renderCitationCards(citations);
  }

  isLoading = false;
  scrollBottom();
  saveChatHistory();

  // Save to search history (defined in search-history.js)
  if (typeof addSearchEntry === 'function') {
    const bubble = document.querySelector('#chatMessages .msg:last-child .bubble-content');
    const preview = bubble ? bubble.textContent || '' : '';
    setTimeout(() => addSearchEntry(query, preview), 100);
  }
}

/* ═══════════════════════════════════════════════
   DOCUMENT UPLOAD
═══════════════════════════════════════════════ */
async function uploadDocument(input) {
  const file = input.files[0];
  if (!file) return;

  // Show progress
  const msgs = document.getElementById('chatMessages');
  const progDiv = document.createElement('div');
  progDiv.className = 'msg msg-assistant';
  progDiv.id = 'uploadProgress';
  progDiv.innerHTML = `<div class="upload-progress"><div class="upload-spinner"></div> Indexing <strong>${escapeHtml(file.name)}</strong>…</div>`;
  msgs.appendChild(progDiv);
  scrollBottom();

  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/api/index-document`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error(`Upload failed: HTTP ${res.status}`);

    const data = await res.json();
    progDiv.remove();
    showToast(`✅ Indexed ${data.chunks || data.documents || 0} chunks from "${file.name}"`);
  } catch (err) {
    progDiv.remove();
    showToast(`❌ Upload error: ${err.message}`);
  }

  input.value = '';
}

/* ═══════════════════════════════════════════════
   DOM HELPERS
═══════════════════════════════════════════════ */
function hideWelcome() {
  document.getElementById('welcomeScreen')?.classList.add('hidden');
}

function addUserBubble(text) {
  const msgs  = document.getElementById('chatMessages');
  const isRTL = currentLang === 'ar' || currentLang === 'ur';

  const div = document.createElement('div');
  div.className = 'msg msg-user';
  div.innerHTML = `
    <div class="bubble bubble-user${isRTL ? ' bubble-arabic' : ''}" dir="${isRTL ? 'rtl' : 'ltr'}">
      ${escapeHtml(text)}
    </div>
  `;
  msgs.appendChild(div);
  scrollBottom();
}

function createAssistantBubble() {
  const msgs = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'msg msg-assistant fade-in';
  div.innerHTML = `
    <div class="bubble bubble-assistant">
      <span class="bubble-content"></span>
      <div class="verse-slot"></div>
    </div>
    <div class="cite-badge invalid"><span></span>Generating answer…</div>
  `;
  msgs.appendChild(div);
  scrollBottom();
  return div;
}

function addAssistantBubble(text, citations, valid) {
  const msgs = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'msg msg-assistant fade-in';

  const highlighted = highlightCitations(escapeHtml(text));
  const verseHtml   = buildVerseDisplay(citations);
  const isValid     = valid !== undefined ? valid : citations.length > 0;

  div.innerHTML = `
    <div class="bubble bubble-assistant">
      <span class="bubble-content">${highlighted}</span>
      ${verseHtml}
    </div>
    <div class="cite-badge ${isValid ? 'valid' : 'invalid'}">
      <span></span>
      ${isValid
        ? `Cited — ${citations.length} source${citations.length !== 1 ? 's' : ''}`
        : 'No citations found — using general knowledge'}
    </div>
  `;

  msgs.appendChild(div);
  addMsgActions(div);
  scrollBottom();
}

function addMsgActions(msgDiv) {
  const existing = msgDiv.querySelector('.msg-actions');
  if (existing) return;

  const actions = document.createElement('div');
  actions.className = 'msg-actions';

  // Copy
  const copyBtn = document.createElement('button');
  copyBtn.className = 'msg-action-btn';
  copyBtn.innerHTML = '📋 Copy';
  copyBtn.title = 'Copy answer';
  copyBtn.onclick = () => {
    const text = msgDiv.querySelector('.bubble-content')?.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied to clipboard');
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      showToast('Copied to clipboard');
    });
  };

  // Feedback: Thumbs Up
  const thumbsUpBtn = document.createElement('button');
  thumbsUpBtn.className = 'msg-action-btn';
  thumbsUpBtn.innerHTML = '👍';
  thumbsUpBtn.title = 'Helpful';
  thumbsUpBtn.dataset.feedbackGiven = 'false';
  thumbsUpBtn.onclick = () => {
    if (thumbsUpBtn.dataset.feedbackGiven === 'true') return;
    thumbsUpBtn.dataset.feedbackGiven = 'true';
    thumbsUpBtn.style.background = 'rgba(26, 92, 56, 0.15)';
    thumbsUpBtn.style.borderColor = 'var(--green-rich)';
    showToast('Thanks for your feedback!');
  };

  // Feedback: Thumbs Down
  const thumbsDownBtn = document.createElement('button');
  thumbsDownBtn.className = 'msg-action-btn';
  thumbsDownBtn.innerHTML = '👎';
  thumbsDownBtn.title = 'Not helpful';
  thumbsDownBtn.dataset.feedbackGiven = 'false';
  thumbsDownBtn.onclick = () => {
    if (thumbsDownBtn.dataset.feedbackGiven === 'true') return;
    thumbsDownBtn.dataset.feedbackGiven = 'true';
    thumbsDownBtn.style.background = 'rgba(180, 60, 40, 0.12)';
    thumbsDownBtn.style.borderColor = '#b43c28';
    showToast('Thanks — we\'ll work on improving!');
  };

  actions.appendChild(copyBtn);
  actions.appendChild(thumbsUpBtn);
  actions.appendChild(thumbsDownBtn);
  msgDiv.appendChild(actions);
}

function addTypingIndicator() {
  const msgs = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'msg msg-assistant';
  div.id = 'typingIndicator';
  div.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  msgs.appendChild(div);
  scrollBottom();
}

function removeTypingIndicator() {
  document.getElementById('typingIndicator')?.remove();
}

function scrollBottom() {
  const msgs = document.getElementById('chatMessages');
  msgs.scrollTo({ top: msgs.scrollHeight, behavior: 'smooth' });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function setStatus(type, text) {
  const dot = document.getElementById('statusDot');
  const label = document.getElementById('statusText');
  if (dot) {
    dot.className = 'status-dot';
    if (type === 'error') dot.classList.add('error');
    else if (type === 'warning') dot.classList.add('warning');
  }
  if (label) label.textContent = text;
}

/* ═══════════════════════════════════════════════
   TOAST
═══════════════════════════════════════════════ */
function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2500);
}

/* ═══════════════════════════════════════════════
   SOURCES & LANGUAGE
═══════════════════════════════════════════════ */
function getSelectedSources() {
  const map = {
    'src-quran':    'quran',
    'src-bukhari':  'hadith_bukhari',
    'src-muslim':   'hadith_muslim',
    'src-dawud':    'hadith_dawud',
    'src-tirmidhi': 'hadith_tirmidhi',
    'src-nasai':    'hadith_nasai',
    'src-ibnmajah': 'hadith_ibnmajah',
    'src-tafsir':   'tafsir',
  };
  return Object.entries(map)
    .filter(([id]) => document.getElementById(id)?.checked)
    .map(([, val]) => val);
}

function toggleSources() {
  document.getElementById('sourcesPanel').classList.toggle('open');
}

function setLang(lang, btn) {
  currentLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const input = document.getElementById('queryInput');
  if (lang === 'ar') {
    input.setAttribute('dir', 'rtl');
    input.placeholder = 'اسألني عن القرآن والحديث والفقه والسيرة…';
  } else if (lang === 'ur') {
    input.setAttribute('dir', 'rtl');
    input.placeholder = 'اسلام کے بارے میں سوال پوچھیں…';
  } else {
    input.setAttribute('dir', 'ltr');
    input.placeholder = 'Ask about Quran, Hadith, Fiqh, Seerah…';
  }
}

/* ═══════════════════════════════════════════════
   INPUT HELPERS
═══════════════════════════════════════════════ */
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendQuery();
  }
}

function useExample(el) {
  const input = document.getElementById('queryInput');
  input.value = el.textContent.trim();
  autoResize(input);
  input.focus();
  sendQuery();
}

/* ═══════════════════════════════════════════════
   DEMO ANSWERS (when backend is offline)
═══════════════════════════════════════════════ */
function getDemoAnswer(query) {
  const q = query.toLowerCase();

  const answers = [
    {
      keywords: ['patience', 'sabr', 'صب', 'صبر'],
      answer: `Patience (Sabr) is one of the greatest virtues in Islam. Allah says: "O you who have believed, seek help through patience and prayer. Indeed, Allah is with the patient." [Quran Al-Baqarah 2:153]

"And We will surely test you with something of fear and hunger and a loss of wealth and lives and fruits, but give good tidings to the patient — those who, when disaster strikes them, say: Indeed we belong to Allah, and indeed to Him we will return." [Quran Al-Baqarah 2:155-156]

The Prophet ﷺ said: "No one has been given anything better than patience." [Bukhari, Zakat, No. 1469] He also said: "How wonderful is the affair of the believer! All his affairs are good. If something good happens to him he is grateful, and if something bad happens to him, he is patient." [Muslim, Zuhd, No. 2999]`
    },
    {
      keywords: ['parent', 'mother', 'father', 'mom', 'dad', 'والد', 'أم', 'أب'],
      answer: `Islam places the highest importance on honoring parents. Allah commands: "And your Lord has decreed that you worship none but Him, and that you be dutiful to your parents. If one of them or both of them reach old age in your life, say not to them a word of disrespect, nor shout at them, but address them in terms of honor." [Quran Al-Isra 17:23]

"And lower to them the wing of humility out of mercy and say: My Lord, have mercy upon them as they brought me up when I was small." [Quran Al-Isra 17:24]

The Prophet ﷺ was asked: "Which deed is the best?" He replied: "Prayer at its proper time." He was asked: "Then what?" He said: "Kindness to parents." [Bukhari, Times of Prayer, No. 527] He also said: "Paradise lies at the feet of mothers." [Ibn Majah, Jihad, No. 2781]`
    },
    {
      keywords: ['zakat', 'zakah', 'زكاة'],
      answer: `Zakat is the third pillar of Islam, an obligatory charity upon every eligible Muslim. Allah commands: "And establish prayer and give zakat, and whatever good you put forward for yourselves, you will find it with Allah." [Quran Al-Baqarah 2:110]

The nisab (minimum threshold) for gold is 85 grams and for silver is 595 grams. The rate is 2.5% of accumulated wealth held for one lunar year.

Allah specifies the eight categories of Zakat recipients: "Zakah expenditures are only for the poor and for the needy and for those employed to collect it and for bringing hearts together and for freeing captives and for those in debt and for the cause of Allah and for the traveler." [Quran At-Tawbah 9:60]

The Prophet ﷺ said: "Islam is built upon five pillars: testifying there is no god but Allah and Muhammad is His Messenger, establishing prayer, giving zakat, performing Hajj, and fasting Ramadan." [Bukhari, Faith, No. 8]`
    },
    {
      keywords: ['music', 'musical', 'song', 'موسيقى', 'غناء'],
      answer: `The majority of Islamic scholars hold that musical instruments (except the duff/hand drum at weddings) are prohibited. Allah says: "And of the people is he who buys the amusement of speech to mislead from the way of Allah without knowledge and who takes it in ridicule." [Quran Luqman 31:6]

Many early scholars — including Ibn Abbas, Ibn Masud, and Ibn Kathir — interpreted "amusement of speech" as singing and musical instruments.

The Prophet ﷺ said: "There will be among my nation people who will make permissible fornication, silk, alcohol, and musical instruments." [Bukhari, Drinks, No. 5590]

However, the duff (hand drum) is permitted at weddings and Eid celebrations. The Prophet said: "Announce the marriage and beat the duff for it." [Tirmidhi, Marriage, No. 1089]`

    },
    {
      keywords: ['fasting', 'sawm', 'ramadan', 'صوم', 'رمضان'],
      answer: `Fasting (Sawm) is the fourth pillar of Islam. Allah commands: "O you who have believed, decreed upon you is fasting as it was decreed upon those before you that you may become righteous." [Quran Al-Baqarah 2:183]

"And whoever among you is ill or on a journey — then an equal number of other days. And upon those who are able — a ransom of feeding a poor person." [Quran Al-Baqarah 2:184]

The month of Ramadan: "The month of Ramadan in which was revealed the Quran, a guidance for mankind and clear proofs of guidance and criterion." [Quran Al-Baqarah 2:185]

The Prophet ﷺ said: "Whoever fasts Ramadan with faith and seeking reward, his previous sins will be forgiven." [Bukhari, Faith, No. 38] He also said: "When Ramadan comes, the gates of Paradise are opened, the gates of Hell are closed, and the devils are chained." [Bukhari, Fasting, No. 1899]`
    },
  ];

  for (const entry of answers) {
    if (entry.keywords.some(kw => q.includes(kw))) {
      return entry.answer;
    }
  }

  // Generic fallback
  return `Bismillah. Thank you for your question about "${query}". 

The FastAPI backend at ${API_BASE} is currently unreachable. Once connected, I will retrieve answers from the Islamic RAG pipeline using ChromaDB vector search across Quran and Hadith collections.

For example, on the topic of honesty in Islam:
"O you who have believed, fear Allah and be with the truthful." [Quran At-Tawbah 9:119]

The Prophet ﷺ said: "Adhere to truthfulness, for truthfulness leads to righteousness, and righteousness leads to Paradise." [Bukhari, Good Manners, No. 6094]

"Truthfulness leads to righteousness, and righteousness leads to Paradise. A man continues to tell the truth until he is recorded with Allah as a truthful person." [Muslim, Virtue, No. 2607]

To get started with the full RAG pipeline, run:
\`uvicorn src.api.main:app --reload\`

Then refresh this page and ask anything about Islam.`
}
