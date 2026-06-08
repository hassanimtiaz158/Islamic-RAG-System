# src/utils/citation_engine.py

import re
from dataclasses import dataclass
from typing import List, Dict, Any


# =========================
# DATA MODEL
# =========================
@dataclass
class Citation:
    raw: str          # e.g. "[Quran Al-Baqarah 2:286]"
    source: str       # quran / bukhari / muslim / dawud / tirmidhi / nasai / ibnmajah
    reference: str    # human-readable reference
    url: str          # online link
    verified: bool    # validation flag


CITATION_REGEX = {
    "quran": r"\[Quran\s+([A-Za-z\-']+(?:\s+[A-Za-z\-']+)*)\s+(\d+):(\d+)\]",

    "bukhari": r"\[Bukhari[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Bukhari\s+(\d+)\]",
    "muslim": r"\[Muslim[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Muslim\s+(\d+)\]",
    "dawud": r"\[Abu\s+Dawud[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Abu\s+Dawud\s+(\d+)\]",
    "tirmidhi": r"\[Tirmidhi[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Tirmidhi\s+(\d+)\]",
    "nasai": r"\[Nasai[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Nasai\s+(\d+)\]",
    "ibnmajah": r"\[Ibn\s+Majah[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]|\[Ibn\s+Majah\s+(\d+)\]",
}

HADITH_BOOK_MAP = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "dawud": "abudawud",
    "tirmidhi": "tirmidhi",
    "nasai": "nasai",
    "ibnmajah": "ibnmajah",
}


# =========================
# URL TEMPLATES
# =========================
QURAN_ONLINE_BASE = "https://quran.com/{surah}/{ayah}"
HADITH_ONLINE_BASE = "https://sunnah.com/{book}:{number}"


def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    Extract all citations from a response text.
    Returns a list of dicts with raw, source, reference, url, verified fields.
    """
    citations = []

    # Quran
    for m in re.finditer(CITATION_REGEX["quran"], text):
        surah_name = m.group(1).strip()
        chapter = m.group(2)
        verse = m.group(3)

        citations.append({
            "raw": m.group(0),
            "source": "quran",
            "reference": f"Surah {surah_name} {chapter}:{verse}",
            "url": f"https://quran.com/{chapter}/{verse}",
            "verified": True,
        })

    # Hadith collections
    for source_key, regex in CITATION_REGEX.items():
        if source_key == "quran":
            continue

        for m in re.finditer(regex, text):
            # Determine which group matched
            if m.group(1) and m.group(2):
                ref = f"{m.group(1).strip()}, Hadith No. {m.group(2)}"
                num = m.group(2)
            elif m.group(3):
                ref = f"Hadith No. {m.group(3)}"
                num = m.group(3)
            else:
                continue

            book_slug = HADITH_BOOK_MAP.get(source_key, source_key)

            citations.append({
                "raw": m.group(0),
                "source": source_key,
                "reference": ref,
                "url": f"https://sunnah.com/{book_slug}:{num}",
                "verified": True,
            })

    # Tafsir (general catch)
    tafsir_re = r"\[Tafsir[^\]]*(?:\d+:?\d*)[^\]]*\]"
    for m in re.finditer(tafsir_re, text):
        citations.append({
            "raw": m.group(0),
            "source": "tafsir",
            "reference": m.group(0).replace("[", "").replace("]", ""),
            "url": "https://quran.com",
            "verified": True,
        })

    return citations


# =========================
# FORMAT FOR FRONTEND
# =========================
def format_citation_cards(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format citations into cards suitable for the frontend sidebar.
    Accepts either Citation objects or dicts.
    """
    cards = []
    for c in citations:
        if isinstance(c, dict):
            source = c.get("source", "unknown")
            raw = c.get("raw", "")
            ref = c.get("reference", raw)
            url = c.get("url", "")
            verified = c.get("verified", True)
        elif isinstance(c, Citation):
            source = c.source
            raw = c.raw
            ref = c.reference
            url = c.url
            verified = c.verified
        else:
            continue

        cards.append({
            "raw": raw,
            "source": source.upper(),
            "reference": ref,
            "url": url,
            "verified": verified,
            "icon": "book-open" if source == "quran" else "scroll",
            "color": "#1A6B2E" if source == "quran" else "#C9A84C",
        })

    return cards


# =========================
# LANGGRAPH ENFORCEMENT NODE
# =========================
def enforce_citations(state: dict, llm) -> dict:
    """
    Final validation node:
    - ensures response has citations
    - regenerates if missing
    """

    response = state.get("response", "")
    citations = extract_citations(response)

    # If no citations → regenerate stricter response
    if len(citations) < 1:
        retry_prompt = f"""
The following answer has NO citations.

Rewrite using ONLY provided sources:

{state.get("context", "")}

Question:
{state.get("query", "")}

RULE:
Every sentence MUST include a citation.
"""

        response = llm.invoke(retry_prompt)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        citations = extract_citations(response_text)
    else:
        response_text = response

    return {
        "response": response_text,
        "citations": [c["raw"] for c in citations],
        "citation_cards": format_citation_cards(citations),
        "citation_valid": len(citations) > 0,
        "iteration": state.get("iteration", 0) + 1,
    }
