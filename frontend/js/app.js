/* ═══════════════════════════════════════════════
   app.js — Main application logic
   WebSocket streaming + REST fallback + UI state
═══════════════════════════════════════════════ */

/* ── Config ── */
const API_BASE   = 'http://localhost:8000';   // Your FastAPI backend
const WS_URL     = 'ws://localhost:8000/ws/ask';

/* ── App state ── */
let currentLang         = 'en';
let conversationHistory = [];
let isLoading           = false;
let ws                  = null;

/* ═══════════════════════════════════════════════
   WEBSOCKET (streaming)
═══════════════════════════════════════════════ */
function connectWebSocket() {
  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('[WS] Connected to FastAPI backend');
      setStatusOnline();
    };

    ws.onmessage = ({ data }) => {
      const msg = JSON.parse(data);

      if (msg.type === 'token') {
        appendStreamToken(msg.content);
      } else if (msg.type === 'done') {
        finalizeStreamResponse(msg);
      }
    };

    ws.onerror = () => {
      console.warn('[WS] WebSocket error — will use REST fallback');
      ws = null;
    };

    ws.onclose = () => {
      console.log('[WS] Connection closed');
      ws = null;
    };
  } catch (e) {
    ws = null;
  }
}

/* Streaming helpers */
let _streamBubble = null;

function appendStreamToken(token) {
  if (!_streamBubble) {
    removeTypingIndicator();
    _streamBubble = createAssistantBubble();
  }
  const content = _streamBubble.querySelector('.bubble-content');
  content.textContent += token;
  scrollBottom();
}

function finalizeStreamResponse(msg) {
  if (_streamBubble) {
    const content = _streamBubble.querySelector('.bubble-content');
    const text    = content.textContent;

    // Replace plain text with highlighted citations
    content.innerHTML = highlightCitations(escapeHtml(text));

    // Verse display
    const citations = msg.citation_cards
      ? msg.citation_cards.map(c => ({ type: c.source.toLowerCase(), raw: c.raw, ref: c.reference, url: c.url }))
      : extractCitations(text);

    const verseEl = _streamBubble.querySelector('.verse-slot');
    if (verseEl) verseEl.innerHTML = buildVerseDisplay(citations);

    // Badge
    const badge = _streamBubble.querySelector('.cite-badge');
    if (badge) {
      const valid = msg.citation_valid || citations.length > 0;
      badge.className = `cite-badge ${valid ? 'valid' : 'invalid'}`;
      badge.innerHTML = `<span></span>${valid ? `Cited — ${citations.length} source${citations.length !== 1 ? 's' : ''}` : 'No citations found'}`;
    }

    renderCitationCards(citations);
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

  conversationHistory.push({ role: 'user', content: query });
  const sources = getSelectedSources();

  // ── Try WebSocket first ──
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      query,
      language: currentLang,
      sources,
    }));
    return; // response handled by ws.onmessage
  }

  // ── REST fallback ──
  try {
    const res = await fetch(`${API_BASE}/api/ask`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, language: currentLang, sources }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data     = await res.json();
    const answer   = data.answer || '';
    const citCards = data.citation_cards || [];

    conversationHistory.push({ role: 'assistant', content: answer });

    const citations = citCards.length
      ? citCards.map(c => ({ type: c.source.toLowerCase(), raw: c.raw, ref: c.reference, url: c.url }))
      : extractCitations(answer);

    removeTypingIndicator();
    addAssistantBubble(answer, citations, data.citation_valid);
    renderCitationCards(citations);

  } catch (err) {
    console.warn('[REST] Backend unreachable, using demo answer:', err.message);
    const demo       = getDemoAnswer(query);
    const citations  = extractCitations(demo);
    conversationHistory.push({ role: 'assistant', content: demo });
    removeTypingIndicator();
    addAssistantBubble(demo, citations, citations.length > 0);
    renderCitationCards(citations);
  }

  isLoading = false;
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
    <div class="cite-badge invalid"><span></span>Checking citations…</div>
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
        : 'No citations found'}
    </div>
  `;
  msgs.appendChild(div);
  scrollBottom();
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

function setStatusOnline() {
  const dot = document.querySelector('.status-dot');
  if (dot) dot.style.background = '#3ac77a';
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
    'src-fiqh':     'fiqh',
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
}

/* ═══════════════════════════════════════════════
   DEMO ANSWERS (when backend is offline)
═══════════════════════════════════════════════ */
function getDemoAnswer(query) {
  const q = query.toLowerCase();

  if (q.includes('patient') || q.includes('sabr')) {
    return `Patience (Sabr) is one of the greatest virtues in Islam. Allah says: "Indeed, Allah is with the patient." [Quran Al-Baqarah 2:153] He also says: "And give good tidings to the patient — those who, when disaster strikes them, say: Indeed we belong to Allah, and indeed to Him we will return." [Quran Al-Baqarah 2:155-156]

The Prophet ﷺ said: "No person has been given anything more generous or more encompassing than patience." [Bukhari, Zakat, No. 1469] He also said: "How wonderful is the affair of the believer! All his affairs are good. If something good happens to him he is grateful, and if something bad happens to him, he is patient." [Muslim, Zuhd, No. 2999]`;
  }

  if (q.includes('parent') || q.includes('mother') || q.includes('father')) {
    return `Islam places the highest importance on honoring parents. Allah commands: "Your Lord has decreed that you worship none but Him, and that you be kind to parents. Whether one or both of them reach old age in your life, say not to them a word of contempt, nor repel them, but address them in terms of honor." [Quran Al-Isra 17:23]

The Prophet ﷺ was asked about the best deed and replied: "Prayer at its prescribed time." When asked what comes next he said: "Honoring your parents." [Bukhari, Times of Prayer, No. 527] He also said: "Paradise lies at the feet of mothers." [Ibn Majah, Jihad, No. 2781]`;
  }

  if (q.includes('music')) {
    return `Scholars have debated music extensively. The majority view holds that most forms of music are prohibited. Allah says: "And of the people is he who buys the amusement of speech to mislead from the way of Allah." [Quran Luqman 31:6] Ibn Masud interpreted this as music and song.

The Prophet ﷺ said: "There will be among my nation people who will make lawful fornication, silk, alcohol, and musical instruments." [Bukhari, Drinks, No. 5590] Commentary on this topic is expanded in [Tafsir Ibn Kathir, Luqman 31:6]. However, the duff (hand drum) is permitted at weddings. [Abu Dawud, Marriage, No. 2097]`;
  }

  if (q.includes('zakat')) {
    return `Zakat is the third pillar of Islam, obligatory on every Muslim with wealth above the nisab. Allah commands: "And establish prayer and give zakat." [Quran Al-Baqarah 2:110]

The nisab for gold is 85 grams and for silver 595 grams. The Prophet ﷺ said: "There is no zakat on wealth less than five awsuq, five camels, or five awaq of silver." [Bukhari, Zakat, No. 1405] The rate is 2.5% of accumulated wealth held for one lunar year (hawl). [Muslim, Zakat, No. 979]

Zakat is distributed to eight categories: "Zakah expenditures are only for the poor and for the needy and for those employed to collect it..." [Quran At-Tawbah 9:60]`;
  }

  return `Bismillah. This is a demo response — your FastAPI backend at ${API_BASE} is currently unreachable. Once connected, all answers will be retrieved from ChromaDB using LangGraph agents across Quran and Hadith collections.

For example, on honesty: "O you who believe, fear Allah and be with the truthful." [Quran At-Tawbah 9:119] The Prophet ﷺ said: "Adhere to truthfulness, for it leads to righteousness, and righteousness leads to Paradise." [Bukhari, Good Manners, No. 6094] He also said: "Truthfulness leads to righteousness." [Muslim, Virtue, No. 2607]

Start your backend with: uvicorn src.api.main:app --reload`;
}

/* ═══════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();

  document.getElementById('queryInput').addEventListener('input', function () {
    autoResize(this);
  });
});
