# src/agents/classifier.py

import json
import re
import logging
from typing import Dict, Any

from src.agents.state import IslamicAgentState
from src.core.islamic_vectorDB import COLLECTIONS

logger = logging.getLogger("islamic-rag.classifier")

CLASSIFY_PROMPT = """\
You are an Islamic knowledge query classifier.

Given a question, identify which Islamic knowledge sources are needed.

Available sources and when to use them:
- "quran": Questions about the Quran, specific verses, what Allah says, Quranic commands
- "hadith_bukhari": Authentic hadith from Bukhari — highest priority for hadith questions
- "hadith_muslim": Sahih Muslim — for additional hadith verification
- "hadith_dawud": Sunan Abu Dawud — hadith about daily life, prayers, transactions
- "hadith_tirmidhi": Jami at-Tirmidhi — hadith about character, explanations, rulings
- "hadith_nasai": Sunan an-Nasai — hadith about worship practices
- "hadith_ibnmajah": Sunan Ibn Majah — supplementary hadith
- "tafsir": Quran interpretation, meaning of verses, commentary
- "fiqh": Islamic rulings, halal/haram, fatawa, jurisprudence
- "seerah": Prophet Muhammad's life, battles, companions, biography

Also classify the question type:
- "quran_exegesis": Interpreting a specific verse
- "hadith_explanation": Understanding a hadith
- "fiqh_ruling": Asking about Islamic law
- "general_knowledge": General knowledge about Islam
- "comparative": Comparing different scholarly opinions
- "historical": Historical Islamic events

Question:
{query}

Respond ONLY with valid JSON (no markdown, no explanation):

{{
  "sources": ["quran", "hadith_bukhari"],
  "type": "fiqh_ruling",
  "priority": "high"
}}
"""

# Keyword-based routing patterns (fallback when LLM is unavailable)
# Phase 4: Added Arabic and Urdu keyword patterns for multilingual support
KEYWORD_ROUTING = {
    "quran": [
        # English
        "quran", "verse", "ayah", "surah", "allah says", "quranic",
        "what does allah say", "what does the quran say", "recite",
        # Arabic
        "قرآن", "آية", "سورة", "الله يقول", "القرآن يقول", "تلاوة",
        "ما يقول الله", "ماذا يقول القرآن", "قران",
        # Urdu
        "قرآن", "آیت", "سورہ", "اللہ فرماتا", "قرآن کہتا",
        "اللہ کیا کہتا", "قرآن کیا کہتا", "تلاوت",
    ],
    "hadith_bukhari": [
        # English
        "hadith", "prophet said", "messenger of allah said",
        "sunnah", "narrated", "bukhari",
        # Arabic
        "حديث", "قال النبي", "قال رسول الله", "سنة", "رواه", "البخاري",
        "حدثنا", "أخبرنا", "بخاری",
        # Urdu
        "حدیث", "نبی نے کہا", "رسول اللہ نے کہا", "سنت", "روایت", "بخاری",
        "حدیث نبوی", "احادیث",
    ],
    "hadith_muslim": [
        # English
        "muslim", "sahih muslim",
        # Arabic
        "مسلم", "صحيح مسلم",
        # Urdu
        "مسلم", "صحیح مسلم",
    ],
    "tafsir": [
        # English
        "tafsir", "interpretation", "meaning of", "commentary",
        "exegesis", "explanation of the verse",
        # Arabic
        "تفسير", "تفسير الآية", "معاني الآية", "شرح الآية", "التفسير",
        "معنى الآية", "شرح",
        # Urdu
        "تفسیر", "تفسیر آیت", "معنی آیت", "تشریح آیت", "تفاسیر",
        "معنی", "تشریح",
    ],
    "fiqh": [
        # English
        "halal", "haram", "ruling", "fatwa", "permitted", "prohibited",
        "obligatory", "recommended", "makruh", "is it allowed",
        "islamic law", "sharia", "fiqh", "prayer", "namaz", "salah",
        # Arabic
        "حلال", "حرام", "حكم", "فتوى", "جائز", "محرم",
        "واجب", "مستحب", "مكروه", "هل يجوز", "الشريعة", "الفقه",
        "حكم شرعي", "فتاوى",
        # Urdu
        "حلال", "حرام", "حکم", "فتویٰ", "جائز", "ناجائز",
        "واجب", "مستحب", "مکروہ", "کیا جائز ہے", "شریعت", "فقہ",
        "حکم شرعی", "فتاوی",
    ],
    "seerah": [
        # English
        "seerah", "biography", "prophet's life", "battles", "companions",
        "hijra", "mecca", "medina", "early islam",
        # Arabic
        "السيرة", "سيرة النبي", "غزوات", "الصحابة", "الهجرة",
        "مكة", "المدينة", "الإسلام المبكر", "السيرة النبوية",
        # Urdu
        "سیرت", "سیرت نبوی", "غزوات", "صحابہ", "ہجرت",
        "مکہ", "مدینہ", "ابتدائی اسلام", "سیرت النبوية",
    ],
}


def classifier_node(state: IslamicAgentState, llm) -> Dict[str, Any]:
    """
    Classifies user query into Islamic knowledge domains
    and determines which collections to retrieve from.
    Uses keyword-based routing (fast, no LLM call needed).
    Falls back to LLM classification only if keywords don't match.
    """
    query = state.get("query", "")

    # Fast path: keyword-based routing (no LLM call)
    keyword_result = _keyword_classify(query)
    if keyword_result["routing"] != ["quran", "hadith_bukhari"] and query.strip():
        # Keywords matched specific sources — use them directly
        return keyword_result

    # Keywords fell back to default — try LLM for better routing
    if llm is not None and query.strip():
        try:
            response = llm.invoke(CLASSIFY_PROMPT.format(query=query))

            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = str(response)

            # Clean up potential markdown (```json ... ``` or ``` ... ```)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                # Drop the opening fence line (including any language tag like "json")
                response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            data = json.loads(response_text)

            sources = data.get("sources", [])
            # Validate sources against the real vector-store collections so all
            # hadith collections (incl. dawud/tirmidhi/nasai/ibnmajah) are kept.
            valid_sources = [s for s in sources if s in COLLECTIONS]

            if valid_sources:
                return {
                    "query_type": data.get("type", "general_knowledge"),
                    "routing": valid_sources,
                }
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, using keyword result")

    return keyword_result


def _keyword_classify(query: str) -> Dict[str, Any]:
    """Keyword-based classification fallback."""
    q = query.lower()
    matched_sources = []

    for source, keywords in KEYWORD_ROUTING.items():
        for keyword in keywords:
            if keyword in q:
                if source not in matched_sources:
                    matched_sources.append(source)
                break

    if not matched_sources:
        matched_sources = ["quran", "hadith_bukhari"]

    return {
        "query_type": _detect_type(q),
        "routing": matched_sources,
    }


def _detect_type(query: str) -> str:
    """Detect question type from keywords (English, Arabic, Urdu)."""
    q = query.lower()
    if any(w in q for w in [
        "meaning", "interpret", "tafsir", "explain this",
        "تفسير", "معنى", "معنی", "تشریح",
    ]):
        return "quran_exegesis"
    if any(w in q for w in [
        "hadith", "narrated", "prophet said",
        "حديث", "رواه", "حدیث", "روایت",
    ]):
        return "hadith_explanation"
    if any(w in q for w in [
        "halal", "haram", "ruling", "fatwa", "law", "is it allowed",
        "حلال", "حرام", "حكم", "فتوى", "هل يجوز",
        "حلال", "حرام", "حکم", "فتویٰ", "کیا جائز",
    ]):
        return "fiqh_ruling"
    if any(w in q for w in [
        "compare", "difference", "opinion", "views", "scholars",
        "فرق", "مقارنة", "آراء", "علماء",
        "فرقہ", "موازنہ", "آراء", "علماء",
    ]):
        return "comparative"
    if any(w in q for w in [
        "battle", "life", "born", "death", "hijra", "history",
        "غزوات", "سيرة", "الهجرة", "تاريخ",
        "غزوات", "سیرت", "ہجرت", "تاریخ",
    ]):
        return "historical"
    return "general_knowledge"
