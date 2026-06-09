# src/agents/classifier.py

import json
import re
import logging
from typing import Dict, Any, List

from src.agents.state import IslamicAgentState

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
KEYWORD_ROUTING = {
    "quran": [
        "quran", "verse", "ayah", "surah", "allah says", "quranic",
        "what does allah say", "what does the quran say", "recite",
    ],
    "hadith_bukhari": [
        "hadith", "prophet said", "messenger of allah said",
        "sunnah", "narrated", "bukhari",
    ],
    "hadith_muslim": [
        "muslim", "sahih muslim",
    ],
    "tafsir": [
        "tafsir", "interpretation", "meaning of", "commentary",
        "exegesis", "explanation of the verse",
    ],
    "fiqh": [
        "halal", "haram", "ruling", "fatwa", "permitted", "prohibited",
        "obligatory", "recommended", "makruh", "is it allowed",
        "islamic law", "sharia", "fiqh",
    ],
    "seerah": [
        "seerah", "biography", "prophet's life", "battles", "companions",
        "hijra", "mecca", "medina", "early islam",
    ],
}


def classifier_node(state: IslamicAgentState, llm) -> Dict[str, Any]:
    """
    Classifies user query into Islamic knowledge domains
    and determines which collections to retrieve from.
    """
    query = state.get("query", "")

    # If no LLM available, use keyword-based routing
    if llm is None:
        return _keyword_classify(query)

    try:
        response = llm.invoke(CLASSIFY_PROMPT.format(query=query))

        if hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response)

        # Clean up potential markdown
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        data = json.loads(response_text)

        sources = data.get("sources", [])
        # Validate sources against known collections
        valid_sources = [s for s in sources if s in KEYWORD_ROUTING]

        if not valid_sources:
            return _keyword_classify(query)

        return {
            "query_type": data.get("type", "general_knowledge"),
            "routing": valid_sources,
        }

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}, falling back to keyword")
        return _keyword_classify(query)


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
    """Detect question type from keywords."""
    q = query.lower()
    if any(w in q for w in ["meaning", "interpret", "tafsir", "explain this"]):
        return "quran_exegesis"
    if any(w in q for w in ["hadith", "narrated", "prophet said"]):
        return "hadith_explanation"
    if any(w in q for w in ["halal", "haram", "ruling", "fatwa", "law", "is it allowed"]):
        return "fiqh_ruling"
    if any(w in q for w in ["compare", "difference", "opinion", "views", "scholars"]):
        return "comparative"
    if any(w in q for w in ["battle", "life", "born", "death", "hijra", "history"]):
        return "historical"
    return "general_knowledge"
