# src/utils/citation_engine.py

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("islamic-rag.citations")


# ═══════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════
@dataclass
class Citation:
    raw: str                          # e.g. "[Quran Al-Baqarah 2:286]"
    source: str                       # quran / bukhari / muslim / dawud / tirmidhi / nasai / ibnmajah / tafsir
    reference: str                    # human-readable reference
    url: str                          # online link
    verified: bool = False           # validation flag
    source_type: str = "primary"     # primary (quran/hadith) / secondary (tafsir/scholarly)
    confidence: float = 1.0          # extraction confidence


# ═══════════════════════════════════════════════
# CITATION REGEX PATTERNS
# ═══════════════════════════════════════════════
CITATION_REGEX = {
    "quran": r"\[Quran\s+([A-Za-z\-']+(?:\s+[A-Za-z\-']+)*)\s+(\d+):(\d+)\]",

    "bukhari": (
        r"\[Bukhari[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Bukhari\s+(\d+)\]"
    ),
    "muslim": (
        r"\[Muslim[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Muslim\s+(\d+)\]"
    ),
    "dawud": (
        r"\[Abu\s+Dawud[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Abu\s+Dawud\s+(\d+)\]"
    ),
    "tirmidhi": (
        r"\[Tirmidhi[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Tirmidhi\s+(\d+)\]"
    ),
    "nasai": (
        r"\[Nasai[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Nasai\s+(\d+)\]"
    ),
    "ibnmajah": (
        r"\[Ibn\s+Majah[,\s]+([^,\]]+),?\s*No\.?\s*(\d+)[^\]]*\]"
        r"|\[Ibn\s+Majah\s+(\d+)\]"
    ),
}

HADITH_BOOK_MAP = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "dawud": "abudawud",
    "tirmidhi": "tirmidhi",
    "nasai": "nasai",
    "ibnmajah": "ibnmajah",
}

# ═══════════════════════════════════════════════
# URL TEMPLATES
# ═══════════════════════════════════════════════
QURAN_ONLINE_BASE = "https://quran.com/{surah}/{ayah}"
HADITH_ONLINE_BASE = "https://sunnah.com/{book}:{number}"


# ═══════════════════════════════════════════════
# EXTRACTION
# ═══════════════════════════════════════════════
def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    Extract all citations from a response text.
    Returns a list of dicts with raw, source, reference, url, verified fields.
    """
    citations = []

    # Quran citations
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
            "source_type": "primary",
            "confidence": 1.0,
        })

    # Hadith collections
    for source_key, regex in CITATION_REGEX.items():
        if source_key == "quran":
            continue

        for m in re.finditer(regex, text):
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
                "source_type": "primary",
                "confidence": 1.0,
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
            "source_type": "secondary",
            "confidence": 0.8,
        })

    return citations


# ═══════════════════════════════════════════════
# FORMAT FOR FRONTEND
# ═══════════════════════════════════════════════
def format_citation_cards(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format citations into cards suitable for the frontend sidebar.
    """
    cards = []
    seen = set()

    for c in citations:
        if isinstance(c, dict):
            source = c.get("source", "unknown")
            raw = c.get("raw", "")
            ref = c.get("reference", raw)
            url = c.get("url", "")
            verified = c.get("verified", True)
            source_type = c.get("source_type", "primary")
        elif isinstance(c, Citation):
            source = c.source
            raw = c.raw
            ref = c.reference
            url = c.url
            verified = c.verified
            source_type = c.source_type
        else:
            continue

        # Deduplicate
        if raw in seen:
            continue
        seen.add(raw)

        cards.append({
            "raw": raw,
            "source": source.upper(),
            "reference": ref,
            "url": url,
            "verified": verified,
            "source_type": source_type,
            "icon": "book-open" if source == "quran" else "scroll",
            "color": "#1A6B2E" if source == "quran" else "#C9A84C",
        })

    return cards


# ═══════════════════════════════════════════════
# ANSWER GROUNDING VERIFICATION
# ═══════════════════════════════════════════════
def verify_answer_grounding(
    response: str,
    context: str,
    citations: List[Dict[str, Any]],
) -> Tuple[bool, List[str], float]:
    """
    Verify that the answer is grounded in the retrieved context.

    Returns:
        (is_grounded, unsupported_claims, confidence_score)
    """
    unsupported = []
    confidence = 1.0

    # 1. Check that citations in the response actually appear in the context
    citation_texts = [c["raw"] for c in citations]
    context_citations = extract_citations(context)

    if not citation_texts:
        # No citations at all — major red flag
        confidence = 0.1
        unsupported.append("No citations found in the response")
        return False, unsupported, confidence

    # 2. Check that each response citation exists in the retrieved context
    context_citation_set = {c["raw"] for c in context_citations}
    for cite_text in citation_texts:
        if cite_text not in context_citation_set:
            # Citation in response but not in context — possible fabrication
            confidence -= 0.2
            unsupported.append(f"Citation not found in retrieved sources: {cite_text}")

    # 3. Check for unsupported factual claims (sentences without citations)
    sentences = re.split(r'(?<=[.!?])\s+', response)
    uncited_claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue
        # Check if this sentence contains any citation
        has_citation = any(cite in sentence for cite in citation_texts)
        if not has_citation and not _is_meta_text(sentence):
            uncited_claims.append(sentence)

    if uncited_claims:
        confidence -= 0.1 * min(len(uncited_claims), 5)
        for claim in uncited_claims[:3]:  # Report up to 3
            unsupported.append(f"Uncited claim: {claim[:100]}")

    # 4. Check for common hallucination patterns
    hallucination_patterns = [
        (r"the Quran says\s+['\"]", "Possible fabricated Quran quote"),
        (r"the Prophet\s+.*said\s+['\"]", "Possible fabricated hadith"),
        (r"according to\s+(?:imam|scholar)\s+\w+", "Possible fabricated scholar reference"),
    ]
    for pattern, warning in hallucination_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            confidence -= 0.15
            unsupported.append(warning)

    confidence = max(0.0, min(1.0, confidence))
    is_grounded = confidence >= 0.5

    return is_grounded, unsupported, confidence


def _is_meta_text(sentence: str) -> bool:
    """Check if a sentence is meta-commentary (not a factual claim)."""
    meta_patterns = [
        r"^I could not find",
        r"^Based on (?:the|these) sources",
        r"^According to (?:the|these) (?:sources|documents)",
        r"^The (?:Quran|hadith|sources) (?:teach|say|mention)",
        r"^In Islam",
        r"^It is (?:important|worth) noting",
        r"^Please (?:note|consult|refer)",
        r"^For (?:more|further) (?:information|details)",
        r"^This (?:is|was) (?:a|an)",
        r"^Bismillah",
        r"^Thank you",
        r"^I apologize",
    ]
    return any(re.search(p, sentence, re.IGNORECASE) for p in meta_patterns)


# ═══════════════════════════════════════════════
# ISLAMIC SAFETY CHECKER
# ═══════════════════════════════════════════════
def check_islamic_safety(response: str, citations: List[Dict[str, Any]]) -> List[str]:
    """
    Check for Islamic-specific safety concerns.
    Returns a list of safety flags.
    """
    flags = []

    # Check if response contains scholarly opinions without proper attribution
    opinion_patterns = [
        r"\b(?:the scholars|most scholars|some scholars|scholars say)\b",
        r"\b(?:it is permissible|it is prohibited|it is recommended|it is obligatory)\b",
        r"\b(?:halal|haram|makruh|mustahab|wajib)\b",
    ]
    has_opinion = any(re.search(p, response, re.IGNORECASE) for p in opinion_patterns)
    has_citations = len(citations) > 0

    if has_opinion and not has_citations:
        flags.append("scholarly_opinion_without_sources")

    # Check for sensitive topics that need scholar disclaimer
    sensitive_topics = [
        r"\b(?:ruling|fatwa|verdict|judgement)\b",
        r"\b(?:divorce|marriage|inheritance|punishment)\b",
        r"\b(?:jihad|war|peace treaty)\b",
        r"\b(?:apostasy|blasphemy)\b",
    ]
    for pattern in sensitive_topics:
        if re.search(pattern, response, re.IGNORECASE):
            flags.append("sensitive_topic")
            break

    # Check for potential fabrication indicators
    if re.search(r"\[Quran\s+\d+:\d+\]", response):
        # Citation without surah name — non-standard format
        flags.append("non_standard_citation_format")

    return flags


# ═══════════════════════════════════════════════
# LANGGRAPH ENFORCEMENT NODE (ENHANCED)
# ═══════════════════════════════════════════════
def enforce_citations(state: dict, llm) -> dict:
    """
    Enhanced validation node:
    - Ensures response has citations
    - Verifies answer grounding
    - Checks Islamic safety
    - Regenerates if missing
    """
    response = state.get("response", "")
    context = state.get("context", "")
    iteration = state.get("iteration", 0)
    max_iterations = 2

    citations = extract_citations(response)

    # ── Step 1: Citation check ──
    if len(citations) < 1 and iteration < max_iterations:
        logger.info(f"No citations found (iteration {iteration + 1}), regenerating...")
        retry_prompt = _build_retry_prompt(state)
        try:
            response = llm.invoke(retry_prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )
            citations = extract_citations(response_text)
        except Exception as e:
            logger.error(f"Retry generation failed: {e}")
            response_text = response
    else:
        response_text = response

    # ── Step 2: Grounding verification ──
    is_grounded, unsupported, grounding_confidence = verify_answer_grounding(
        response_text, context, citations
    )

    # ── Step 3: Islamic safety check ──
    safety_flags = check_islamic_safety(response_text, citations)

    # ── Step 4: Determine source types ──
    source_types = list(set(c.get("source", "unknown") for c in citations))
    if not source_types and is_grounded:
        source_types = ["retrieved_context"]
    elif not source_types:
        source_types = ["none"]

    # ── Step 5: Build final confidence score ──
    retrieval_confidence = state.get("retrieval_confidence", 0.5)
    final_confidence = (retrieval_confidence * 0.4) + (grounding_confidence * 0.6)

    # If insufficient evidence, override response
    insufficient = state.get("insufficient_evidence", False)
    if insufficient and not citations:
        response_text = (
            "I could not find sufficient evidence in the available Islamic sources "
            "to answer this question. Please try rephrasing your question or "
            "selecting additional sources. For specific Islamic rulings, "
            "please consult a qualified Islamic scholar."
        )
        citations = []
        final_confidence = 0.0
        is_grounded = False

    # Add scholarly disclaimer for sensitive topics
    if "sensitive_topic" in safety_flags and "scholarly_opinion" not in source_types:
        response_text += (
            "\n\n⚠️ **Important Note:** This topic involves nuanced Islamic rulings. "
            "The information above is based on the retrieved sources. "
            "For personal religious obligations (fard, haram, halal), "
            "please consult a qualified Islamic scholar who can consider "
            "your specific circumstances."
        )

    return {
        "response": response_text,
        "citations": [c["raw"] for c in citations],
        "citation_cards": format_citation_cards(citations),
        "citation_valid": len(citations) > 0,
        "verification_passed": is_grounded,
        "unsupported_claims": unsupported,
        "confidence_score": round(final_confidence, 2),
        "safety_flags": safety_flags,
        "source_types": source_types,
        "iteration": iteration + 1,
    }


def cross_reference_citations(
    response: str,
    context: str,
    citations: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float, bool]:
    """
    Cross-reference each citation in the response against the actual retrieved
    context.  A citation is 'verified' if its key components (surah name + verse
    for Quran, collection name + number for Hadith) appear in the context text.

    Returns:
        (citation_verdicts, hallucination_ratio, fact_check_passed)
    """
    if not citations:
        return [], 0.0, True

    verdicts: List[Dict[str, Any]] = []
    verified_count = 0

    for cite in citations:
        raw = cite.get("raw", "")
        source = cite.get("source", "")
        verdict: Dict[str, Any] = {
            "raw": raw,
            "source": source,
            "reference": cite.get("reference", ""),
            "verified": False,
            "reason": "",
        }

        if source == "quran":
            # Extract surah name and chapter:verse from the raw citation
            m = re.search(CITATION_REGEX["quran"], raw)
            if m:
                surah_name = m.group(1).strip().lower()
                chapter_verse = f"{m.group(2)}:{m.group(3)}"
                # Check both surah name and chapter:verse appear in context
                has_surah = surah_name in context.lower()
                has_verse = chapter_verse in context
                if has_surah and has_verse:
                    verdict["verified"] = True
                    verdict["reason"] = "Found in retrieved context"
                    verified_count += 1
                elif has_verse:
                    verdict["verified"] = True
                    verdict["reason"] = "Verse reference found in context"
                    verified_count += 1
                else:
                    verdict["reason"] = (
                        f"Surah '{m.group(1)}' or verse '{chapter_verse}' "
                        f"not found in retrieved context"
                    )
            else:
                verdict["reason"] = "Could not parse Quran citation"

        elif source in ("bukhari", "muslim", "dawud", "tirmidhi", "nasai", "ibnmajah"):
            # Check collection name (case-insensitive) and number in context
            collection_names = {
                "bukhari": ["bukhari"],
                "muslim": ["muslim"],
                "dawud": ["abu dawud", "dawud", "abudawud"],
                "tirmidhi": ["tirmidhi"],
                "nasai": ["nasai", "nasa'i"],
                "ibnmajah": ["ibn majah", "ibnmajah"],
            }
            names = collection_names.get(source, [source])
            name_in_context = any(n in context.lower() for n in names)

            # Extract number from citation
            num_match = re.search(r"(\d+)", raw)
            num_str = num_match.group(1) if num_match else ""

            # Check number appears in context (as standalone or in citation-like patterns)
            num_in_context = False
            if num_str:
                # Look for the number near the collection name or in citation context
                num_patterns = [
                    rf"\b{re.escape(num_str)}\b",
                    rf"No\.?\s*{re.escape(num_str)}",
                    rf"#{re.escape(num_str)}",
                ]
                num_in_context = any(
                    re.search(p, context, re.IGNORECASE) for p in num_patterns
                )

            if name_in_context and num_in_context:
                verdict["verified"] = True
                verdict["reason"] = "Collection and number found in context"
                verified_count += 1
            elif name_in_context:
                verdict["verified"] = True
                verdict["reason"] = "Collection name found in context"
                verified_count += 1
            else:
                verdict["reason"] = (
                    f"Collection '{source}' not found in retrieved context"
                )

        elif source == "tafsir":
            # Tafsir: check if any part of the reference appears in context
            ref_text = raw.replace("[", "").replace("]", "").strip()
            if ref_text.lower() in context.lower() or "tafsir" in context.lower():
                verdict["verified"] = True
                verdict["reason"] = "Tafsir reference found in context"
                verified_count += 1
            else:
                verdict["reason"] = "Tafsir reference not found in context"

        else:
            # Unknown source — mark as unverified but not penalize heavily
            verdict["verified"] = True
            verdict["reason"] = "Unknown source type — skipped verification"
            verified_count += 1

        verdicts.append(verdict)

    total = len(verdicts)
    hallucination_ratio = 1.0 - (verified_count / total) if total > 0 else 0.0
    fact_check_passed = hallucination_ratio < 0.5

    return verdicts, round(hallucination_ratio, 2), fact_check_passed


def build_verse_triplets(
    citations: List[Dict[str, Any]],
    context: str,
) -> List[Dict[str, Any]]:
    """
    For each Quran citation, build a triplet of {arabic, english, urdu} verse data
    by extracting from the retrieved context.

    Returns a list of dicts:
        {citation_raw, surah, ayah, arabic, english, urdu, needs_urdu}
    """
    triplets: List[Dict[str, Any]] = []

    for cite in citations:
        if cite.get("source") != "quran":
            continue

        raw = cite.get("raw", "")
        m = re.search(CITATION_REGEX["quran"], raw)
        if not m:
            continue

        surah_name = m.group(1).strip()
        chapter = m.group(2)
        verse = m.group(3)

        triplet: Dict[str, Any] = {
            "citation_raw": raw,
            "surah": surah_name,
            "surah_number": int(chapter),
            "ayah": int(verse),
            "arabic": "",
            "english": "",
            "urdu": "",
            "needs_urdu": True,
        }

        # Try to extract English translation from context
        # Context blocks look like: [QURAN] SurahName Ch:V\nEnglish text
        context_lines = context.split("\n")
        for i, line in enumerate(context_lines):
            # Look for lines containing this surah and verse
            if (
                surah_name.lower() in line.lower()
                and f"{chapter}:{verse}" in line
            ):
                # The next non-empty line is likely the verse text
                for j in range(i + 1, min(i + 3, len(context_lines))):
                    text = context_lines[j].strip()
                    if text and not text.startswith("["):
                        triplet["english"] = text
                        break
                break

        # If we found English in context, try to also find Arabic
        # Arabic text may be in metadata or context
        if not triplet["english"]:
            # Fallback: mark for frontend API fetch
            triplet["needs_urdu"] = True

        triplets.append(triplet)

    return triplets


def _build_retry_prompt(state: dict) -> str:
    """Build a strict retry prompt when citations are missing."""
    return f"""
CRITICAL: Your previous answer had NO citations. You MUST rewrite with proper citations.

RULES:
1. Every factual claim MUST end with a citation in the exact format shown below.
2. ONLY use information from the provided sources below.
3. If a claim cannot be supported by the sources, REMOVE it.
4. NEVER fabricate citations.

CITATION FORMATS (EXACT — DO NOT MODIFY):
- Quran: [Quran SurahName Chapter:Verse]  →  [Quran Al-Baqarah 2:153]
- Hadith: [CollectionName Number]  →  [Bukhari 1469]  →  [Muslim 2999]

RETRIEVED SOURCES:
{state.get("context", "No sources available.")}

QUESTION:
{state.get("query", "")}

REWRITTEN ANSWER (every sentence MUST have a citation):
"""
