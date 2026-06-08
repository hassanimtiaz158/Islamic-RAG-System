# src/agents/classifier.py

import json
from typing import Dict, Any

from src.agents.state import IslamicAgentState


CLASSIFY_PROMPT = """
You are an Islamic knowledge classifier.

Given a question, identify which knowledge sources are needed.

Respond ONLY with valid JSON. No explanation.

Available sources:
- "quran": Questions about Quran, specific verses, what Allah says
- "hadith_bukhari": Authentic hadith, Prophet's sayings/actions (high priority)
- "hadith_muslim": Additional authentic hadith verification
- "hadith_dawud": Hadith about daily life, prayers, rituals
- "tafsir": Quran interpretation, meaning of verses
- "fiqh": Islamic rulings, halal/haram, fatawa
- "seerah": Prophet's life, battles, companions

Question:
{query}

Return format:
{{
  "sources": ["quran", "hadith_bukhari"],
  "type": "fiqh"
}}

Respond ONLY with JSON:
"""


def classifier_node(state: IslamicAgentState, llm) -> Dict[str, Any]:
    """
    Classifies user query into Islamic knowledge domains
    and determines which collections to retrieve from.
    """

    # If no LLM available, return safe defaults
    if llm is None:
        return {
            "query_type": "general",
            "routing": ["quran", "hadith_bukhari"],
        }

    try:
        # Call LLM
        response = llm.invoke(
            CLASSIFY_PROMPT.format(query=state["query"])
        )

        # Some LLMs return object, some return string
        if hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response)

        # Parse JSON safely
        data = json.loads(response_text.strip())

        return {
            "query_type": data.get("type", "general"),
            "routing": data.get(
                "sources",
                ["quran", "hadith_bukhari"],
            ),
        }

    except Exception:
        # Safe fallback (always works)
        return {
            "query_type": "general",
            "routing": ["quran", "hadith_bukhari"],
        }
