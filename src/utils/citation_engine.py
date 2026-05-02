import re
from dataclasses import dataclass
from typing import List, Dict, Any


# =========================
# DATA MODEL
# =========================
@dataclass
class Citation:
    raw: str          # e.g. "[Quran Al-Baqarah 2:286]"
    source: str       # quran / bukhari / muslim
    reference: str    # human-readable reference
    url: str          # online link
    verified: bool    # validation flag


CITATION_REGEX = {
    "quran": r"\[Quran\s+([A-Za-z\-\'\s]+)\s+(\d+):(\d+)\]",

    "bukhari": r"\[Bukhari\s+(\d+)\]",

    "muslim": r"\[Muslim\s+(\d+)\]",

    "dawud": r"\[Abu\s+Dawud\s+(\d+)\]",

    "tirmidhi": r"\[Tirmidhi\s+(\d+)\]",
}





# =========================
# URL TEMPLATES
# =========================
QURAN_ONLINE_BASE = "https://quran.com/{surah}/{ayah}"
HADITH_ONLINE_BASE = "https://sunnah.com/{book}:{number}"


def extract_citations(text: str):
    citations = []

    # Quran
    for m in re.finditer(CITATION_REGEX["quran"], text):
        surah, chapter, verse = m.group(1), m.group(2), m.group(3)

        citations.append({
            "raw": m.group(0),
            "source": "quran",
            "reference": f"{surah or 'Surah'} {chapter}:{verse}",
        })

    # Hadith (ALL SAME LOGIC NOW)
    for source in ["bukhari", "muslim", "dawud", "tirmidhi"]:
        for m in re.finditer(CITATION_REGEX[source], text):
            citations.append({
                "raw": m.group(0),
                "source": source,
                "reference": f"Hadith No. {m.group(1)}",
            })

    return citations


# =========================
# FORMAT FOR FRONTEND
# =========================
def format_citation_cards(citations: List[Citation]) -> List[Dict[str, Any]]:
    return [
        {
            "raw": c.raw,
            "source": c.source.upper(),
            "reference": c.reference,
            "url": c.url,
            "verified": c.verified,
            "icon": "book-open" if c.source == "quran" else "scroll",
            "color": "#1A6B2E" if c.source == "quran" else "#C9A84C",
        }
        for c in citations
    ]


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
        "citations": [c.raw for c in citations],
        "citation_cards": format_citation_cards(citations),
        "citation_valid": len(citations) > 0,
        "iteration": state.get("iteration", 0) + 1,
    }
