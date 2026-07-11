/* ═══════════════════════════════════════════════
   citations.js — Citation extraction, rendering,
   and verification helpers
═══════════════════════════════════════════════ */

// ── Regex patterns matching the citation_engine.py format ──
const CITATION_PATTERNS = [
  // Quran
  { regex: /\[Quran\s+([A-Za-z\-']+(?:\s+[A-Za-z\-']+)*)\s+(\d+):(\d+)\]/g, type: 'quran' },
  // Hadith collections
  { regex: /\[Bukhari[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  { regex: /\[Muslim[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  { regex: /\[Abu\s+Dawud[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  { regex: /\[Tirmidhi[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  { regex: /\[Nasai[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  { regex: /\[Ibn\s+Majah[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]/gi, type: 'hadith' },
  // Shorthand: [Bukhari 1], [Muslim 89] etc.
  { regex: /\[Bukhari\s+(\d+)\]/g, type: 'hadith' },
  { regex: /\[Muslim\s+(\d+)\]/g, type: 'hadith' },
  { regex: /\[Abu\s+Dawud\s+(\d+)\]/g, type: 'hadith' },
  { regex: /\[Tirmidhi\s+(\d+)\]/g, type: 'hadith' },
  { regex: /\[Nasai\s+(\d+)\]/g, type: 'hadith' },
  { regex: /\[Ibn\s+Majah\s+(\d+)\]/g, type: 'hadith' },
  // Tafsir
  { regex: /\[Tafsir[^\]]*(?:\d+:?\d*)[^\]]*\]/g, type: 'tafsir' },
];

const ICON_MAP  = { quran: '📖', hadith: '📜', tafsir: '🔍' };
const LABEL_MAP = { quran: 'Quran', hadith: 'Hadith', tafsir: 'Tafsir' };

/** Cache for Quran API lookups */
const verseCache = {};

/**
 * Prefill the verse cache from backend-provided verse triplets so the UI can
 * render without hitting the external AlQuran.cloud API. Any language the
 * backend did not supply (often empty) is left for the async fetch to fill.
 * @param {Array} triplets - backend verse_triplets [{surah_number, ayah, arabic, english, urdu}]
 */
function ingestVerseTriplets(triplets) {
  if (!Array.isArray(triplets)) return;
  triplets.forEach(t => {
    if (!t || t.surah_number == null || t.ayah == null) return;
    const key = `${t.surah_number}:${t.ayah}`;
    const prev = verseCache[key] || {};
    verseCache[key] = {
      arabic: t.arabic || prev.arabic || '',
      english: t.english || prev.english || '',
      urdu: t.urdu || prev.urdu || '',
      transliteration: prev.transliteration || '',
    };
  });
}

/**
 * Extract all citations from an answer string.
 * @param {string} text
 * @returns {{ raw:string, type:string, ref:string, url:string }[]}
 */
function extractCitations(text) {
  const found = [];
  const seen = new Set();

  CITATION_PATTERNS.forEach(({ regex, type }) => {
    const re = new RegExp(regex.source, 'g');
    let m;
    while ((m = re.exec(text)) !== null) {
      // Deduplicate
      const key = m[0].trim();
      if (seen.has(key)) continue;
      seen.add(key);

      let ref = '';
      let url = '';

      if (type === 'quran' && m[1] && m[2] && m[3]) {
        const surahName = m[1].trim();
        const chapter = m[2];
        const verse = m[3];
        ref = `Surah ${surahName}, Verse ${verse}`;
        url = `https://quran.com/${chapter}/${verse}`;
      } else if (type === 'hadith') {
        // Multi-group pattern: [Bukhari Book, No. 1234]
        if (m[1] && m[2]) {
          ref = `${m[1].trim()}, Hadith ${m[2]}`;
          const raw = m[0].toLowerCase();
          const book = raw.includes('bukhari')  ? 'bukhari'
                     : raw.includes('muslim')   ? 'muslim'
                     : raw.includes('abu')      ? 'abudawud'
                     : raw.includes('tirmidhi') ? 'tirmidhi'
                     : raw.includes('nasai')    ? 'nasai'
                     : 'ibnmajah';
          url = `https://sunnah.com/${book}:${m[2]}`;
        }
        // Shorthand: [Bukhari 1234]
        else if (m[1]) {
          ref = `Hadith No. ${m[1]}`;
          const raw = m[0].toLowerCase();
          const book = raw.includes('bukhari')  ? 'bukhari'
                     : raw.includes('muslim')   ? 'muslim'
                     : raw.includes('abu')      ? 'abudawud'
                     : raw.includes('tirmidhi') ? 'tirmidhi'
                     : raw.includes('nasai')    ? 'nasai'
                     : 'ibnmajah';
          url = `https://sunnah.com/${book}:${m[1]}`;
        }
      } else if (type === 'tafsir') {
        ref = m[0].replace(/^\[|\]$/g, '');
        url = 'https://quran.com';
      }

      found.push({ raw: m[0], type, ref, url });
    }
  });

  return found;
}

/**
 * Wrap citation tags in the answer text with styled spans.
 * @param {string} text
 * @returns {string} HTML string
 */
function highlightCitations(text) {
  let result = text;
  CITATION_PATTERNS.forEach(({ regex }) => {
    const re = new RegExp(regex.source, 'g');
    result = result.replace(re, match =>
      `<span class="cite-inline" title="${match.replace(/"/g, '&quot;')}">${match}</span>`
    );
  });
  // Convert newlines to <br> for proper paragraph rendering
  result = result.replace(/\n/g, '<br>');
  return result;
}

/**
 * Build the Arabic verse display block for the first Quran citation.
 * Uses AlQuran.cloud API with caching.
 * @param {{ type:string, raw:string, ref:string }[]} citations
 * @returns {string} HTML string
 */
function buildVerseDisplay(citations) {
  const quranCite = citations.find(c => c.type === 'quran');
  if (!quranCite) return '';

  // Try to extract surah and ayah from the raw citation
  const match = quranCite.raw.match(/(\d+):(\d+)/);
  if (!match) return '';

  const surah = match[1];
  const ayah = match[2];

  // Trigger async lookup (result injected via callback)
  lookupVerseArabic(surah, ayah);

  const cacheKey = `${surah}:${ayah}`;
  const cached = verseCache[cacheKey];

  if (cached) {
    return `
      <div class="verse-display">
        <div class="verse-arabic">${cached.arabic}</div>
        <div class="verse-transliteration">${cached.transliteration || ''}</div>
        <div class="verse-ref">${quranCite.ref || quranCite.raw}</div>
      </div>
    `;
  }

  // Placeholder while loading
  return `
    <div class="verse-display verse-loading" data-surah="${surah}" data-ayah="${ayah}">
      <div class="verse-arabic" style="opacity:0.4">Loading verse…</div>
      <div class="verse-ref">${quranCite.ref || quranCite.raw}</div>
    </div>
  `;
}

/**
 * Look up Arabic verse text from AlQuran.cloud API.
 * @param {number|string} surah
 * @param {number|string} ayah
 */
async function lookupVerseArabic(surah, ayah) {
  const cacheKey = `${surah}:${ayah}`;
  if (verseCache[cacheKey]) return;

  try {
    const res = await fetch(`https://api.alquran.cloud/v1/ayah/${surah}:${ayah}`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();

    if (data.code === 200 && data.data) {
      verseCache[cacheKey] = {
        arabic: data.data.text,
        transliteration: '', // API doesn't provide transliteration directly
      };

      // Update any verse-loading elements
      document.querySelectorAll(`.verse-loading[data-surah="${surah}"][data-ayah="${ayah}"]`).forEach(el => {
        el.classList.remove('verse-loading');
        const arabicEl = el.querySelector('.verse-arabic');
        if (arabicEl) {
          arabicEl.textContent = data.data.text;
          arabicEl.style.opacity = '';
        }
      });
    }
  } catch (e) {
    console.warn('[CITATION] Failed to fetch verse:', e);
    // Fallback to placeholder
    document.querySelectorAll(`.verse-loading[data-surah="${surah}"][data-ayah="${ayah}"]`).forEach(el => {
      el.classList.remove('verse-loading');
      const arabicEl = el.querySelector('.verse-arabic');
      if (arabicEl) {
        arabicEl.textContent = '—';
        arabicEl.style.opacity = '0.4';
      }
    });
  }
}

// ═══════════════════════════════════════════════
// VERSE TRIPLET — Arabic + English + Urdu display
// ═══════════════════════════════════════════════

/**
 * Fetch a verse in all three languages (Arabic, English, Urdu).
 * Uses AlQuran.cloud for Arabic/English, and backend /api/translate-verse for Urdu.
 * Results are cached keyed by "surah:ayah".
 *
 * @param {number|string} surah
 * @param {number|string} ayah
 * @returns {Promise<{arabic: string, english: string, urdu: string}>}
 */
async function fetchVerseTriplet(surah, ayah) {
  const cacheKey = `${surah}:${ayah}`;

  // Check if we already have all three languages cached
  if (verseCache[cacheKey] && verseCache[cacheKey].arabic && verseCache[cacheKey].english && verseCache[cacheKey].urdu) {
    return verseCache[cacheKey];
  }

  const result = { arabic: '', english: '', urdu: '' };

  try {
    // Fetch Arabic and English in parallel
    const [arabicRes, englishRes] = await Promise.all([
      fetch(`https://api.alquran.cloud/v1/ayah/${surah}:${ayah}`),
      fetch(`https://api.alquran.cloud/v1/ayah/${surah}:${ayah}/en.yusufali`),
    ]);

    if (arabicRes.ok) {
      const data = await arabicRes.json();
      if (data.code === 200 && data.data) {
        result.arabic = data.data.text;
      }
    }

    if (englishRes.ok) {
      const data = await englishRes.json();
      if (data.code === 200 && data.data) {
        result.english = data.data.text;
      }
    }

    // Fetch Urdu translation from backend
    if (result.english) {
      try {
        const urduRes = await fetch(`${API_BASE}/api/translate-verse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: result.english, target_lang: 'ur' }),
        });
        if (urduRes.ok) {
          const urduData = await urduRes.json();
          result.urdu = urduData.translated || '';
        }
      } catch (urduErr) {
        console.warn('[TRIPLET] Urdu translation fetch failed:', urduErr);
      }
    }
  } catch (e) {
    console.warn('[TRIPLET] Failed to fetch verse triplet:', e);
  }

  // Cache the result
  verseCache[cacheKey] = { ...verseCache[cacheKey], ...result };

  return result;
}

/**
 * Build side-by-side Arabic/English/Urdu verse display for all Quran citations.
 * @param {{ type:string, raw:string, ref:string }[]} citations
 * @returns {string} HTML string with triplet cards
 */
function buildVerseTripletDisplay(citations) {
  const quranCites = citations.filter(c => c.type === 'quran');
  if (!quranCites.length) return '';

  const containers = quranCites.map(cite => {
    // Extract surah and ayah from citation like [Quran Al-Baqarah 2:153]
    const match = cite.raw.match(/(\d+):(\d+)/);
    if (!match) return '';

    const surah = match[1];
    const ayah = match[2];
    const cacheKey = `${surah}:${ayah}`;
    const cached = verseCache[cacheKey];

    // If fully cached, render immediately
    if (cached && cached.arabic && cached.english) {
      return renderTripletCard(surah, ayah, cached.arabic, cached.english, cached.urdu || '', cite.ref || cite.raw, true);
    }

    // Otherwise render loading card and trigger async fetch
    fetchVerseTriplet(surah, ayah).then(triplet => {
      updateTripletCard(surah, ayah, triplet);
    });

    return renderTripletCard(surah, ayah, '', '', '', cite.ref || cite.raw, false);
  });

  return containers.filter(Boolean).join('');
}

/**
 * Render a single triplet card HTML.
 */
function renderTripletCard(surah, ayah, arabic, english, urdu, ref, isReady) {
  const opacityStyle = isReady ? '' : 'opacity:0.4;';
  return `
    <div class="verse-triplet-wrapper" data-triplet-key="${surah}:${ayah}">
      <div class="verse-triplet" style="${!isReady ? 'opacity:0.5;' : ''}">
        <div class="verse-col verse-col-arabic" dir="rtl">
          <div class="verse-lang-label">العربية</div>
          <div class="verse-text verse-arabic-text">${arabic || 'جاري التحميل…'}</div>
        </div>
        <div class="verse-col verse-col-english">
          <div class="verse-lang-label">English</div>
          <div class="verse-text verse-english-text">${english || 'Loading…'}</div>
        </div>
        <div class="verse-col verse-col-urdu" dir="rtl">
          <div class="verse-lang-label">اردو</div>
          <div class="verse-text verse-urdu-text">${urdu || 'لوڈ ہو رہا ہے…'}</div>
        </div>
      </div>
      <div class="verse-triplet-ref">${ref.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
    </div>
  `;
}

/**
 * Update a triplet card in the DOM after async fetch completes.
 */
function updateTripletCard(surah, ayah, triplet) {
  const key = `${surah}:${ayah}`;
  const wrapper = document.querySelector(`.verse-triplet-wrapper[data-triplet-key="${key}"]`);
  if (!wrapper) return;

  const card = wrapper.querySelector('.verse-triplet');
  if (card) card.style.opacity = '';

  const arabicEl = wrapper.querySelector('.verse-arabic-text');
  const englishEl = wrapper.querySelector('.verse-english-text');
  const urduEl = wrapper.querySelector('.verse-urdu-text');

  if (arabicEl && triplet.arabic) arabicEl.textContent = triplet.arabic;
  if (englishEl && triplet.english) englishEl.textContent = triplet.english;
  if (urduEl && triplet.urdu) urduEl.textContent = triplet.urdu;
  else if (urduEl && !triplet.urdu) urduEl.textContent = 'Translation unavailable';
}

/**
 * Render citation cards into the sidebar.
 * @param {{ raw:string, type:string, ref:string, url:string }[]} citations
 */
function renderCitationCards(citations) {
  const list  = document.getElementById('citationsList');
  const empty = document.getElementById('citationsEmpty');
  const countEl = document.getElementById('citationCount');

  if (!citations.length) return;

  empty.classList.add('hidden');

  citations.forEach((c, i) => {
    // Skip if already rendered
    const existing = list.querySelector(`[data-raw="${CSS.escape(c.raw)}"]`);
    if (existing) return;

    const card = document.createElement('div');
    card.className = `citation-card ${c.type}`;
    card.dataset.raw = c.raw;
    card.style.animationDelay = `${i * 60}ms`;

    const verifiedEl = (c.type === 'quran')
      ? '<span class="card-verified pending">… Verifying</span>'
      : '<span class="card-verified">✓ Verified</span>';

    card.innerHTML = `
      <div class="card-source">
        <div class="card-icon ${c.type}">${ICON_MAP[c.type] || '📄'}</div>
        <span class="card-source-label ${c.type}">${LABEL_MAP[c.type] || 'Source'}</span>
        ${verifiedEl}
      </div>
      <div class="card-reference">${(c.ref || c.raw).replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      <div class="card-raw">${c.raw.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      <a class="card-link" href="${c.url}" target="_blank" rel="noopener">View Source</a>
    `;

    list.appendChild(card);

    // For Quran cards, verify the reference through the backend and update the badge.
    if (c.type === 'quran') {
      const ref = parseQuranRef(c.raw);
      if (ref) {
        const badge = card.querySelector('.card-verified');
        verifyQuranCitation(ref.surah, ref.ayah).then((r) => {
          if (!badge) return;
          if (r.verified) {
            badge.classList.remove('pending');
            badge.textContent = '✓ Verified';
          } else {
            badge.classList.remove('pending');
            badge.classList.add('unverified');
            badge.textContent = '⚠ Not verified';
          }
        });
      }
    }
  });

  // Update count badge
  const totalCards = list.querySelectorAll('.citation-card').length;
  countEl.textContent = totalCards;
}

/**
 * Verify a Quran citation. Goes through the backend /api/verify-citation
 * proxy (which calls AlQuran.cloud) so the browser never needs a direct
 * cross-origin request. Resolves to { verified, text, surahName } or
 * { verified: false }.
 * @param {number} surah
 * @param {number} ayah
 */
async function verifyQuranCitation(surah, ayah) {
  try {
    const base = window.__API_BASE__ || '';
    const res  = await fetch(`${base}/api/verify-citation?q=${surah}:${ayah}`);
    if (!res.ok) return { verified: false };
    const data = await res.json();
    if (data && data.verified) {
      return {
        verified:  true,
        text:      data.text,
        surahName: data.surahName,
      };
    }
    return { verified: false };
  } catch (e) {
    return { verified: false };
  }
}

/**
 * Parse "surah:ayah" out of a Quran citation raw string such as
 * "[Quran Al-Baqarah 2:255]". Returns { surah, ayah } or null.
 * @param {string} raw
 */
function parseQuranRef(raw) {
  const m = String(raw || '').match(/(\d+)\s*:\s*(\d+)/);
  if (!m) return null;
  const surah = parseInt(m[1], 10);
  const ayah  = parseInt(m[2], 10);
  if (surah < 1 || surah > 114 || ayah < 1) return null;
  return { surah, ayah };
}
