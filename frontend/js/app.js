/* ═══════════════════════════════════════════════
   app.js — Main application logic
   WebSocket streaming + REST fallback + UI state
   Enhanced v2: confidence scores, verification badges
═══════════════════════════════════════════════ */

/* ── Config ── */
const API_BASE = 'https://islamic-rag-system.onrender.com' || '';
const WS_URL     = API_BASE
  ? API_BASE.replace(/^http/, 'ws') + '/ws/ask'
  : ((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/ask');

// In production (Vercel), WebSocket to external Render backend may be blocked.
const IS_VERCEL = !API_BASE && (window.location.hostname.includes('.vercel.app') || window.location.hostname.includes('vercel.app'));

/* ── App state ── */
let currentLang         = 'en';
let isLoading           = false;
let ws                  = null;
let reconnectTimer      = null;
let _streamBubble       = null;
let _streamMeta         = {};  // metadata for current stream (confidence, verification, etc.)
let currentConversationId = null;  // multi-turn conversation session ID

/* ── Multilingual UI strings (Phase 4) ── */
const UI_STRINGS = {
  generating: { en: 'Generating answer…', ar: 'جاري إنشاء الإجابة…', ur: 'جواب تیار کیا جا رہا ہے…' },
  connecting: { en: 'Connecting to backend…', ar: 'جاري الاتصال بالخادم…', ur: 'بیک اینڈ سے رابطہ کیا جا رہا ہے…' },
  connected:  { en: 'Connected to backend', ar: 'متصل بالخادم', ur: 'بیک اینڈ سے منسلک' },
  disconnected: { en: 'Backend unavailable — using local knowledge', ar: 'الخادم غير متاح — استخدام المعرفة المحلية', ur: 'بیک اینڈ دستیاب نہیں — مقامی علم کا استعمال' },
  no_citations: { en: 'No citations found — using general knowledge', ar: 'لم يتم العثور على استشهادات — استخدام المعرفة العامة', ur: 'کوئی حوالے نہیں ملے — عام علم کا استعمال' },
  cited_sources: { en: 'Cited — {n} source{s}', ar: 'مستشهد — {n} مصدر{s}', ur: 'حوالہ دیا گیا — {n} ذریعہ{s}' },
  verified:   { en: 'Verified', ar: 'تم التحقق', ur: 'تصدیق شدہ' },
  not_verified: { en: 'Not verified', ar: 'لم يتم التحقق', ur: 'تصدیق نہیں ہوئی' },
  confidence: { en: 'confidence', ar: 'ثقة', ur: 'اعتماد' },
  sensitive_topic: { en: 'Sensitive topic — please consult a qualified scholar', ar: 'موضوع حساس — يرجى استشارة عالم مؤهل', ur: 'حساس موضوع — براہ کرم ایک مستند عالم سے مشورہ کریں' },
  chat_cleared: { en: 'Chat cleared', ar: 'تم مسح المحادثة', ur: 'چیٹ صاف کر دی گئی' },
  copied:     { en: 'Copied to clipboard', ar: 'تم النسخ إلى الحافظة', ur: 'کلپ بورڈ پر کاپی ہو گیا' },
  feedback_thanks: { en: 'Thanks for your feedback!', ar: 'شكرًا لتعليقاتك!', ur: 'آپ کے فیڈبیک کا شکریہ!' },
  feedback_improve: { en: "Thanks — we'll work on improving!", ar: 'شكرًا — سنعمل على التحسين!', ur: 'شکریہ — ہم بہتری پر کام کریں گے!' },
};

function getUiString(key, n) {
  const entry = UI_STRINGS[key] || {};
  let text = entry[currentLang] || entry.en || key;
  if (n !== undefined) {
    text = text.replace('{n}', n).replace('{s}', n !== 1 ? (currentLang === 'ar' ? 'ات' : (currentLang === 'ur' ? 'یں' : 's')) : '');
  }
  return text;
}

/* ═══════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  restoreTheme();
  restoreLang();
  restoreChatHistory();
  connectWebSocket();
  checkBackendHealth();

  document.getElementById('queryInput').addEventListener('input', function () {
    autoResize(this);
  });
});

/* ═══════════════════════════════════════════════
   BACKEND HEALTH CHECK
═══════════════════════════════════════════════ */
let _healthCheckTimer = null;

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.rag_available) {
        setStatus('online', 'Connected to backend (RAG ready)');
      } else if (data.rag_error) {
        // Backend is up but RAG failed to init — show actionable error
        const errMsg = data.rag_error;
        const actionHint = errMsg.includes('API key') || errMsg.includes('required')
          ? ' Set your API key in .env or ensure Ollama is running.'
          : '';
        setStatus('error', `RAG error: ${errMsg}${actionHint}`);
      } else {
        setStatus('warning', 'Connected — RAG pipeline loading…');
        // Retry in 3s until RAG is ready
        if (_healthCheckTimer) clearTimeout(_healthCheckTimer);
        _healthCheckTimer = setTimeout(checkBackendHealth, 3000);
      }
    } else {
      setStatus('warning', 'Backend unavailable — using local knowledge');
    }
  } catch (e) {
    setStatus('warning', 'Backend unavailable — using local knowledge');
  }
}

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
  const confirmMsg = currentLang === 'ar' ? 'مسح جميع الرسائل؟' : (currentLang === 'ur' ? 'تمام پیغامات صاف کریں؟' : 'Clear all chat messages?');
  if (!confirm(confirmMsg)) return;
  const msgs = document.getElementById('chatMessages');
  msgs.querySelectorAll('.msg').forEach(el => el.remove());
  const list = document.getElementById('citationsList');
  list.querySelectorAll('.citation-card').forEach(el => el.remove());
  document.getElementById('citationCount').textContent = '0';
  document.getElementById('citationsEmpty').classList.remove('hidden');
  document.getElementById('welcomeScreen').classList.remove('hidden');
  localStorage.removeItem(STORAGE_KEY);
  showToast(getUiString('chat_cleared'));
}

/* ═══════════════════════════════════════════════
   WEBSOCKET (streaming)
═══════════════════════════════════════════════ */
function connectWebSocket() {
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
    // Timeout if connection doesn't open within 5s
    const connTimeout = setTimeout(() => {
      if (ws && ws.readyState !== WebSocket.OPEN) {
        console.warn('[WS] Connection timeout');
        try { ws.close(); } catch (e) { /* ignore */ }
        ws = null;
        setStatus('warning', 'WebSocket timeout — using REST');
      }
    }, 5000);

    ws.onopen = () => {
      clearTimeout(connTimeout);
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
      clearTimeout(connTimeout);
      console.warn('[WS] WebSocket error — will use REST fallback');
      setStatus('warning', 'WebSocket failed, using REST');
      ws = null;
    };

    ws.onclose = () => {
      clearTimeout(connTimeout);
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
  // Remove any partially-streamed bubble so the user doesn't see a half-written answer
  if (_streamBubble) {
    _streamBubble.remove();
    _streamBubble = null;
  }
  const retryMsg = currentLang === 'ar' ? 'يرجى إعادة صياغة سؤالك أو اختيار مصادر مختلفة.' : (currentLang === 'ur' ? 'براہ کرم اپنا سوال دوبارہ لکھیں یا مختلف ذرائع منتخب کریں۔' : 'Please try rephrasing your question or select different sources.');
  addAssistantBubble(
    `⚠️ ${message}\n\n${retryMsg}`,
    [], false
  );
  isLoading = false;
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

function renderFollowUpChips(container, questions) {
  const chipsDiv = document.createElement('div');
  chipsDiv.className = 'followup-chips';
  questions.forEach(q => {
    const chip = document.createElement('button');
    chip.className = 'followup-chip';
    chip.textContent = q;
    chip.addEventListener('click', () => {
      const input = document.getElementById('queryInput');
      input.value = q;
      input.dispatchEvent(new Event('input'));
      sendQuery();
    });
    chipsDiv.appendChild(chip);
  });
  container.appendChild(chipsDiv);
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

      // Capture conversation ID for multi-turn
      if (msg.conversation_id) {
        currentConversationId = msg.conversation_id;
      }

      // Verse display (Arabic + English + Urdu triplet)
      const verseEl = _streamBubble.querySelector('.verse-slot');
      if (verseEl) {
        if (msg.verse_triplets && msg.verse_triplets.length) ingestVerseTriplets(msg.verse_triplets);
        verseEl.innerHTML = buildVerseDisplay(citations) + buildVerseTripletDisplay(citations);
      }

      // Update meta badge with enhanced info
      updateMetaBadge(msg, citations);

      // Follow-up question chips
      if (msg.follow_up_questions && msg.follow_up_questions.length > 0) {
        renderFollowUpChips(_streamBubble, msg.follow_up_questions);
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

  // ── Try WebSocket first ──
  if (!IS_VERCEL && ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({
        query,
        language: currentLang,
        sources,
        conversation_id: currentConversationId || '',
      }));
      return;
    } catch (e) {
      // ws.send() can throw if the socket closes between the readyState check
      // and the call. Drop the socket and fall through to the REST path.
      console.warn('[WS] send failed, falling back to REST:', e);
      ws = null;
    }
  }

  // ── REST fallback ──
  try {
    setStatus('warning', 'Querying backend via REST…');
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout for RAG

    const res = await fetch(`${API_BASE}/api/ask`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, language: currentLang, sources, conversation_id: currentConversationId || '' }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data     = await res.json();
    const answer   = data.answer || '';
    const citCards = data.citation_cards || [];

    // Capture conversation ID for multi-turn
    if (data.conversation_id) {
      currentConversationId = data.conversation_id;
    }

    const citations = citCards.length
      ? citCards.map(c => ({
          type: (c.source || 'hadith').toLowerCase(),
          raw: c.raw || c.reference || '',
          ref: c.reference || '',
          url: c.url || ''
        }))
      : extractCitations(answer);

    // Build enhanced meta with new fields
    const enhancedData = {
      ...data,
      citation_valid: data.citation_valid !== undefined ? data.citation_valid : citations.length > 0,
      confidence_score: data.confidence_score || 0,
      verification_passed: data.verification_passed || false,
      source_types: data.source_types || [],
      safety_flags: data.safety_flags || [],
    };

    removeTypingIndicator();
    addAssistantBubbleEnhanced(answer, citations, enhancedData, data.follow_up_questions || [], data.verse_triplets || []);
    renderCitationCards(citations);
    setStatus('online', 'Connected to backend');

  } catch (err) {
    console.warn('[REST] Backend error:', err.message);
    setStatus('warning', 'Backend unavailable — using local knowledge');

    const errorMsg = err.name === 'AbortError'
      ? 'The server took too long to respond. The RAG pipeline may be loading — try again in a moment.'
      : null;
    const demo      = getDemoAnswer(query);
    const citations = extractCitations(demo);
    removeTypingIndicator();
    const introMsg = errorMsg ? `${errorMsg}\n\n` : '';
    addAssistantBubbleEnhanced(`${introMsg}${demo}`, citations, {
      citation_valid: citations.length > 0,
      confidence_score: 0.3,
      verification_passed: false,
      source_types: [],
      safety_flags: [],
      insufficient_evidence: true,
    });
    renderCitationCards(citations);
  }

  isLoading = false;
  scrollBottom();
  saveChatHistory();

  // Save to search history
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
   ENHANCED DOM HELPERS
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
    <div class="meta-row">
      <div class="cite-badge invalid"><span></span>${getUiString('generating')}</div>
      <div class="confidence-indicator" style="display:none">
        <div class="confidence-bar">
          <div class="confidence-fill"></div>
        </div>
        <span class="confidence-label"></span>
      </div>
    </div>
    <div class="verification-row" style="display:none">
      <span class="verification-badge"></span>
      <div class="source-types"></div>
    </div>
  `;
  msgs.appendChild(div);
  scrollBottom();
  return div;
}

function addAssistantBubble(text, citations, valid) {
  addAssistantBubbleEnhanced(text, citations, {
    citation_valid: valid,
    confidence_score: valid ? 0.7 : 0.1,
    verification_passed: valid,
    source_types: [],
    safety_flags: [],
  });
}

function addAssistantBubbleEnhanced(text, citations, meta, followUps, verseTriplets) {
  const msgs = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'msg msg-assistant fade-in';

  const lang = meta.language || currentLang;
  const isRTL = lang === 'ar' || lang === 'ur';
  const bubbleClass = lang === 'ur' ? 'bubble-urdu' : (lang === 'ar' ? 'bubble-arabic' : '');

  const highlighted = highlightCitations(escapeHtml(text));
  // Prefill verse cache from backend triplets (when supplied) so the verse
  // display renders without an extra external API call.
  if (verseTriplets && verseTriplets.length) ingestVerseTriplets(verseTriplets);
  const verseHtml   = buildVerseDisplay(citations) + buildVerseTripletDisplay(citations);
  const isValid = meta.citation_valid !== undefined ? meta.citation_valid : citations.length > 0;
  const confidence = meta.confidence_score || 0;

  // Follow-up question chips (rendered programmatically to avoid inline handler XSS)
  let followUpHtml = '';
  if (followUps && followUps.length > 0) {
    const chipsDiv = document.createElement('div');
    chipsDiv.className = 'followup-chips';
    followUps.forEach(q => {
      const chip = document.createElement('button');
      chip.className = 'followup-chip';
      chip.textContent = q;
      chip.addEventListener('click', () => {
        const input = document.getElementById('queryInput');
        input.value = q;
        input.dispatchEvent(new Event('input'));
        sendQuery();
      });
      chipsDiv.appendChild(chip);
    });
    // Serialize to HTML string for insertion into innerHTML
    followUpHtml = chipsDiv.outerHTML;
  }

  div.innerHTML = `
    <div class="bubble bubble-assistant ${bubbleClass}" dir="${isRTL ? 'rtl' : 'ltr'}">
      <span class="bubble-content">${highlighted}</span>
      ${verseHtml}
    </div>
    <div class="meta-row">
      <div class="cite-badge ${isValid ? 'valid' : 'invalid'}">
        <span></span>
        ${isValid
          ? getUiString('cited_sources', citations.length)
          : getUiString('no_citations')}
      </div>
      <div class="confidence-indicator">
        <div class="confidence-bar">
          <div class="confidence-fill" style="width: ${confidence * 100}%"></div>
        </div>
        <span class="confidence-label">${Math.round(confidence * 100)}% ${getUiString('confidence')}</span>
      </div>
    </div>
    <div class="verification-row" style="${meta.verification_passed === undefined ? 'display:none' : ''}">
      <span class="verification-badge ${meta.verification_passed ? 'passed' : 'failed'}">
        ${meta.verification_passed ? '✓ ' + getUiString('verified') : '⚠ ' + getUiString('not_verified')}
      </span>
      <div class="source-types">
        ${(meta.source_types || []).map(st => `<span class="source-type-tag ${st}">${st.replace(/_/g, ' ')}</span>`).join('')}
      </div>
    </div>
    ${(meta.safety_flags || []).includes('sensitive_topic')
      ? `<div class="safety-notice">⚠️ ${getUiString('sensitive_topic')}</div>`
      : ''}
    ${followUpHtml}
  `;

  msgs.appendChild(div);

  // Re-attach follow-up chip listeners (innerHTML serialisation strips them)
  div.querySelectorAll('.followup-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const input = document.getElementById('queryInput');
      input.value = chip.textContent;
      input.dispatchEvent(new Event('input'));
      sendQuery();
    });
  });

  addMsgActions(div);
  scrollBottom();
}

function updateMetaBadge(msg, citations) {
  if (!_streamBubble) return;

  // Citation badge
  const badge = _streamBubble.querySelector('.cite-badge');
  if (badge) {
    const valid = citations.length > 0;
    badge.className = `cite-badge ${valid ? 'valid' : 'invalid'}`;
    badge.innerHTML = `<span></span>${valid
      ? getUiString('cited_sources', citations.length)
      : getUiString('no_citations')}`;
  }

  // Confidence bar
  const confIndicator = _streamBubble.querySelector('.confidence-indicator');
  if (confIndicator) {
    confIndicator.style.display = 'flex';
    const fill = confIndicator.querySelector('.confidence-fill');
    const label = confIndicator.querySelector('.confidence-label');
    const score = msg.confidence_score || 0;
    if (fill) fill.style.width = `${score * 100}%`;
    if (label) label.textContent = `${Math.round(score * 100)}% ${getUiString('confidence')}`;
  }

  // Verification row
  const verifyRow = _streamBubble.querySelector('.verification-row');
  if (verifyRow && msg.verification_passed !== undefined) {
    verifyRow.style.display = 'flex';
    const vBadge = verifyRow.querySelector('.verification-badge');
    const srcTypes = verifyRow.querySelector('.source-types');
    if (vBadge) {
      vBadge.className = `verification-badge ${msg.verification_passed ? 'passed' : 'failed'}`;
      vBadge.textContent = msg.verification_passed ? '✓ ' + getUiString('verified') : '⚠ ' + getUiString('not_verified');
    }
    if (srcTypes) {
      srcTypes.innerHTML = (msg.source_types || [])
        .map(st => `<span class="source-type-tag ${st}">${st.replace(/_/g, ' ')}</span>`)
        .join('');
    }
  }

  // Safety notice
  const flags = msg.safety_flags || [];
  if (flags.includes('sensitive_topic')) {
    const existing = _streamBubble.querySelector('.safety-notice');
    if (!existing) {
      const notice = document.createElement('div');
      notice.className = 'safety-notice';
      notice.innerHTML = '⚠️ ' + getUiString('sensitive_topic');
      _streamBubble.appendChild(notice);
    }
  }
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
      showToast(getUiString('copied'));
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      showToast(getUiString('copied'));
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
    showToast(getUiString('feedback_thanks'));
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
    showToast(getUiString('feedback_improve'));
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
  const selected = Object.entries(map)
    .filter(([id]) => document.getElementById(id)?.checked)
    .map(([, val]) => val);
  // Never send an empty list — an empty `sources` would make the backend
  // retrieve nothing. Fall back to the default collections instead.
  return selected.length ? selected : ['quran', 'hadith_bukhari'];
}

function toggleSources() {
  document.getElementById('sourcesPanel').classList.toggle('open');
}

function restoreLang() {
  const saved = localStorage.getItem('alilm-lang');
  if (saved && ['en', 'ar', 'ur'].includes(saved)) {
    currentLang = saved;
    const btn = document.querySelector(`.lang-btn[data-lang="${saved}"]`);
    if (btn) {
      document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const input = document.getElementById('queryInput');
      if (saved === 'ar') {
        input.setAttribute('dir', 'rtl');
        input.placeholder = 'اسألني عن القرآن والحديث والفقه والسيرة…';
      } else if (saved === 'ur') {
        input.setAttribute('dir', 'rtl');
        input.placeholder = 'اسلام کے بارے میں سوال پوچھیں…';
      } else {
        input.setAttribute('dir', 'ltr');
        input.placeholder = 'Ask about Quran, Hadith, Fiqh, Seerah…';
      }
    }
  }
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
  localStorage.setItem('alilm-lang', lang);
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

The Prophet ﷺ said: "No one has been given anything better than patience." [Bukhari 1469] He also said: "How wonderful is the affair of the believer! All his affairs are good. If something good happens to him he is grateful, and if something bad happens to him, he is patient." [Muslim 2999]`
    },
    {
      keywords: ['parent', 'mother', 'father', 'mom', 'dad', 'والد', 'أم', 'أب'],
      answer: `Islam places the highest importance on honoring parents. Allah commands: "And your Lord has decreed that you worship none but Him, and that you be dutiful to your parents. If one of them or both of them reach old age in your life, say not to them a word of disrespect, nor shout at them, but address them in terms of honor." [Quran Al-Isra 17:23]

"And lower to them the wing of humility out of mercy and say: My Lord, have mercy upon them as they brought me up when I was small." [Quran Al-Isra 17:24]

The Prophet ﷺ was asked: "Which deed is the best?" He replied: "Prayer at its proper time." He was asked: "Then what?" He said: "Kindness to parents." [Bukhari 527] He also said: "Paradise lies at the feet of mothers." [Ibn Majah 2781]`
    },
    {
      keywords: ['zakat', 'zakah', 'زكاة'],
      answer: `Zakat is the third pillar of Islam, an obligatory charity upon every eligible Muslim. Allah commands: "And establish prayer and give zakat, and whatever good you put forward for yourselves, you will find it with Allah." [Quran Al-Baqarah 2:110]

The nisab (minimum threshold) for gold is 85 grams and for silver is 595 grams. The rate is 2.5% of accumulated wealth held for one lunar year.

Allah specifies the eight categories of Zakat recipients: "Zakah expenditures are only for the poor and for the needy and for those employed to collect it and for bringing hearts together and for freeing captives and for those in debt and for the cause of Allah and for the traveler." [Quran At-Tawbah 9:60]

The Prophet ﷺ said: "Islam is built upon five pillars: testifying there is no god but Allah and Muhammad is His Messenger, establishing prayer, giving zakat, performing Hajj, and fasting Ramadan." [Bukhari 8]`
    },
    {
      keywords: ['music', 'musical', 'song', 'موسيقى', 'غناء'],
      answer: `The majority of Islamic scholars hold that musical instruments (except the duff/hand drum at weddings) are prohibited. Allah says: "And of the people is he who buys the amusement of speech to mislead from the way of Allah without knowledge and who takes it in ridicule." [Quran Luqman 31:6]

The Prophet ﷺ said: "There will be among my nation people who will make permissible fornication, silk, alcohol, and musical instruments." [Bukhari 5590]

However, the duff (hand drum) is permitted at weddings and Eid celebrations. [Tirmidhi 1089]`
    },
    {
      keywords: ['fasting', 'sawm', 'ramadan', 'صوم', 'رمضان'],
      answer: `Fasting (Sawm) is the fourth pillar of Islam. Allah commands: "O you who have believed, decreed upon you is fasting as it was decreed upon those before you that you may become righteous." [Quran Al-Baqarah 2:183]

"The month of Ramadan in which was revealed the Quran, a guidance for mankind and clear proofs of guidance and criterion." [Quran Al-Baqarah 2:185]

The Prophet ﷺ said: "Whoever fasts Ramadan with faith and seeking reward, his previous sins will be forgiven." [Bukhari 38] He also said: "When Ramadan comes, the gates of Paradise are opened, the gates of Hell are closed, and the devils are chained." [Bukhari 1899]`
    },
  ];

  // Phase 4: Add Arabic demo answers
  if (currentLang === 'ar') {
    const arabicAnswers = [
      { keywords: ['صبر', 'صبور'], answer: `الصبر من أعظم الفضائل في الإسلام. يقول الله تعالى: "يا أيها الذين آمنوا استعينوا بالصبر والصلاة وإن الله مع الصابرين." [Quran Al-Baqarah 2:153]\n\nوقال النبي ﷺ: "ما أُعطي أحدٌ عطاءً خيرًا وأوسع من الصبر." [Bukhari 1469]` },
      { keywords: ['بر الوالدين', 'أم', 'أب', 'والد'], answer: `Islam places the highest importance on honoring parents. Allah says: "وقضى ربك ألا تعبدوا إلا إياه وبالوالدين إحسانًا." [Quran Al-Isra 17:23]\n\nThe Prophet ﷺ said: "الجنة تحت أقدام الأمهات." [Ibn Majah 2781]` },
    ];
    for (const entry of arabicAnswers) {
      if (entry.keywords.some(kw => q.includes(kw))) return entry.answer;
    }
  }

  // Phase 4: Add Urdu demo answers
  if (currentLang === 'ur') {
    const urduAnswers = [
      { keywords: ['صبر', 'برداشت'], answer: `صبر اسلام میں سب سے بڑی فضیلتوں میں سے ایک ہے۔ اللہ تعالیٰ فرماتا ہے: "اے ایمان والو! صبر اور نماز کے ذریعے مدد مانگو بے شک اللہ صبر کرنے والوں کے ساتھ ہے۔" [Quran Al-Baqarah 2:153]\n\nنبی ﷺ نے فرمایا: "صبر سے بہتر کوئی عطا نہیں دی گئی۔" [Bukhari 1469]` },
      { keywords: ['والدین', 'ماں', 'باپ'], answer: `اسلام میں والدین کا احترام سب سے اہم ہے۔ اللہ تعالیٰ فرماتا ہے: "اپنے رب نے حکم دیا ہے کہ آپ اس کے سوا کسی کی عبادت نہ کریں اور والدین کے ساتھ حسن سلوک کریں۔" [Quran Al-Isra 17:23]\n\nنبی ﷺ نے فرمایا: "جنت ماں کے پاؤں تلے ہے۔" [Ibn Majah 2781]` },
    ];
    for (const entry of urduAnswers) {
      if (entry.keywords.some(kw => q.includes(kw))) return entry.answer;
    }
  }

  // Default fallback — language-aware
  if (currentLang === 'ar') {
    return `بسم الله. شكراً لسؤالك عن "${query}".\n\nالخادم غير متصل حالياً. يرجى تشغيل الخادم الخلفي للحصول على إجابات كاملة:\n\`uvicorn src.api.main:app --reload\``;
  }
  if (currentLang === 'ur') {
    return `بسم اللہ۔ "${query}" کے سوال کا شکریہ۔\n\nبیک اینڈ ابھی غیر متصل ہے۔ مکمل جوابات کے لیے بیک اینڈ چلائیں:\n\`uvicorn src.api.main:app --reload\``;
  }

  return `Bismillah. Thank you for your question about "${query}".

The FastAPI backend is currently unreachable. Once connected, answers will be retrieved from the Islamic RAG pipeline using vector search across Quran and Hadith collections with source verification and confidence scoring.

To get started with the full RAG pipeline, run:
\`uvicorn src.api.main:app --reload\`

Then refresh this page and ask anything about Islam.`;
}
