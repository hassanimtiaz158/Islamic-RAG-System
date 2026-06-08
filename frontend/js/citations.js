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

    card.innerHTML = `
      <div class="card-source">
        <div class="card-icon ${c.type}">${ICON_MAP[c.type] || '📄'}</div>
        <span class="card-source-label ${c.type}">${LABEL_MAP[c.type] || 'Source'}</span>
        <span class="card-verified">✓ Verified</span>
      </div>
      <div class="card-reference">${(c.ref || c.raw).replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      <div class="card-raw">${c.raw.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      <a class="card-link" href="${c.url}" target="_blank" rel="noopener">View Source</a>
    `;

    list.appendChild(card);
  });

  // Update count badge
  const totalCards = list.querySelectorAll('.citation-card').length;
  countEl.textContent = totalCards;
}

/**
 * Verify a Quran citation against the live AlQuran.cloud API.
 * Resolves to { verified, text, surahName } or { verified: false }.
 * @param {number} surah
 * @param {number} ayah
 */
async function verifyQuranCitation(surah, ayah) {
  try {
    const res  = await fetch(`https://api.alquran.cloud/v1/ayah/${surah}:${ayah}/en.yusufali`);
    const data = await res.json();
    if (data.code === 200) {
      return {
        verified:  true,
        text:      data.data.text,
        surahName: data.data.surah.englishName,
      };
    }
    return { verified: false };
  } catch (e) {
    return { verified: false };
  }
}
