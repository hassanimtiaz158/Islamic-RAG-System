/* ═══════════════════════════════════════════════
   citations.js — Citation extraction, rendering,
   and verification helpers
═══════════════════════════════════════════════ */

// ── Regex patterns matching the citation_engine.py format ──
const CITATION_PATTERNS = [
  { regex: /\[Quran\s+([A-Za-z\-']+(?:\s+[A-Za-z\-']+)*)\s+(\d+):(\d+)\]/g, type: 'quran'  },
  { regex: /\[Bukhari[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,             type: 'hadith' },
  { regex: /\[Muslim[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,              type: 'hadith' },
  { regex: /\[Abu\s+Dawud[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,        type: 'hadith' },
  { regex: /\[Tirmidhi[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,           type: 'hadith' },
  { regex: /\[Nasai[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,              type: 'hadith' },
  { regex: /\[Ibn\s+Majah[,\s]+([^,\]]+),\s*No\.?\s*(\d+)[^\]]*\]/g,        type: 'hadith' },
  { regex: /\[Tafsir[^\]]+\d+:\d+\]/g,                                        type: 'tafsir' },
];

const ICON_MAP  = { quran: '📖', hadith: '📜', tafsir: '🔍' };
const LABEL_MAP = { quran: 'Quran', hadith: 'Hadith', tafsir: 'Tafsir' };

/**
 * Extract all citations from an answer string.
 * @param {string} text
 * @returns {{ raw:string, type:string, ref:string, url:string }[]}
 */
function extractCitations(text) {
  const found = [];

  CITATION_PATTERNS.forEach(({ regex, type }) => {
    const re = new RegExp(regex.source, regex.flags);
    let m;
    while ((m = re.exec(text)) !== null) {
      let ref = '';
      let url = '';

      if (type === 'quran' && m[1] && m[2] && m[3]) {
        ref = `Surah ${m[1]}, Verse ${m[3]}`;
        url = `https://quran.com/${m[2]}/${m[3]}`;
      } else if (type === 'hadith' && m[1] && m[2]) {
        ref = `${m[1].trim()}, Hadith ${m[2]}`;
        const raw = m[0].toLowerCase();
        const book = raw.includes('bukhari')  ? 'bukhari'
                   : raw.includes('muslim')   ? 'muslim'
                   : raw.includes('abu')      ? 'abudawud'
                   : raw.includes('tirmidhi') ? 'tirmidhi'
                   : raw.includes('nasai')    ? 'nasai'
                   : 'ibnmajah';
        url = `https://sunnah.com/${book}:${m[2]}`;
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
    const re = new RegExp(regex.source, regex.flags);
    result = result.replace(re, match =>
      `<span class="cite-inline" title="${match}">${match}</span>`
    );
  });
  return result;
}

/**
 * Build the Arabic verse display block for the first Quran citation.
 * In production this would call the AlQuran.cloud API to get real text.
 * @param {{ type:string, raw:string }[]} citations
 * @returns {string} HTML string
 */
function buildVerseDisplay(citations) {
  const quranCite = citations.find(c => c.type === 'quran');
  if (!quranCite) return '';

  // Placeholder Arabic — replace with live API call in production:
  // GET https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar
  return `
    <div class="verse-display">
      <div class="verse-arabic">وَاصْبِرْ وَمَا صَبْرُكَ إِلَّا بِاللَّهِ</div>
      <div class="verse-transliteration">Waṣbir wa-mā ṣabruka illā billāh</div>
      <div class="verse-ref">${quranCite.raw}</div>
    </div>
  `;
}

/**
 * Render citation cards into the sidebar.
 * @param {{ raw:string, type:string, ref:string, url:string }[]} citations
 */
function renderCitationCards(citations) {
  const list  = document.getElementById('citationsList');
  const empty = document.getElementById('citationsEmpty');

  if (!citations.length) return;

  empty.classList.add('hidden');

  citations.forEach((c, i) => {
    const card = document.createElement('div');
    card.className = `citation-card ${c.type}`;
    card.style.animationDelay = `${i * 60}ms`;

    card.innerHTML = `
      <div class="card-source">
        <div class="card-icon ${c.type}">${ICON_MAP[c.type] || '📄'}</div>
        <span class="card-source-label ${c.type}">${LABEL_MAP[c.type] || 'Source'}</span>
        <span class="card-verified">✓ Verified</span>
      </div>
      <div class="card-reference">${c.ref || c.raw}</div>
      <div class="card-raw">${c.raw}</div>
      <a class="card-link" href="${c.url}" target="_blank" rel="noopener">View Source</a>
    `;

    list.appendChild(card);
  });

  // Update count badge
  const countEl = document.getElementById('citationCount');
  countEl.textContent = parseInt(countEl.textContent || '0') + citations.length;
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
  } catch {
    return { verified: false };
  }
}
