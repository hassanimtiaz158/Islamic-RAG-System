# src/utils/translator.py
"""
LLM-based translation layer for Al-Ilm Islamic RAG System.

Supports: English (en), Arabic (ar), Urdu (ur)
Approach: Uses the LLM itself for translation — no external translation APIs needed.
Modern LLMs (phi3, llama3, GPT) have strong Urdu and Arabic capabilities.
"""

import logging

logger = logging.getLogger("islamic-rag.translator")

# In-memory translation cache: {(text_hash, src, tgt): translated_text}
_translation_cache: dict = {}
_CACHE_MAX_SIZE = 500

# ═══════════════════════════════════════════════
# LANGUAGE NAMES (for prompts)
# ═══════════════════════════════════════════════
LANGUAGE_NAMES = {
    "en": "English",
    "ar": "Arabic (الفصحى - Modern Standard Arabic)",
    "ur": "Urdu (اردو)",
}

# ═══════════════════════════════════════════════
# UI STRINGS (for frontend-backend shared messages)
# ═══════════════════════════════════════════════
UI_STRINGS = {
    "insufficient_evidence": {
        "en": (
            "I could not find sufficient evidence in the available Islamic sources "
            "to answer this question. Please try rephrasing your question or "
            "selecting additional sources. For specific Islamic rulings, "
            "please consult a qualified Islamic scholar."
        ),
        "ar": (
            "لم أتمكن من العثور على أدلة كافية في المصادر الإسلامية المتاحة "
            "للإجابة على هذا السؤال. يرجى إعادة صياغة سؤالك أو اختيار مصادر إضافية. "
            "للأحكام الإسلامية المحددة، يرجى استشارة عالم إسلامي مؤهل."
        ),
        "ur": (
            "میں دستیاب اسلامی ذرائع میں اس سوال کا جواب دینے کے لیے کافی دلیل "
            "نہیں ڈھونڈ سکا۔ براہ کرم اپنا سوال دوبارہ لکھیں یا مزید ذرائع منتخب کریں۔ "
            "مخصوص اسلامی احکام کے لیے، براہ کرم ایک مستند اسلامی عالم سے مشورہ کریں۔"
        ),
    },
    "error_generating": {
        "en": "I encountered an error generating the answer. Please try again.",
        "ar": "حدث خطأ أثناء إنشاء الإجابة. يرجى المحاولة مرة أخرى.",
        "ur": "جواب تیار کرنے میں خرابی آئی۔ براہ کرم دوبارہ کوشش کریں۔",
    },
    "scholar_disclaimer": {
        "en": (
            "\n\n⚠️ **Important Note:** This topic involves nuanced Islamic rulings. "
            "The information above is based on the retrieved sources. "
            "For personal religious obligations (farāḍ, ḥarām, ḥalāl), "
            "please consult a qualified Islamic scholar who can consider "
            "your specific circumstances."
        ),
        "ar": (
            "\n\n⚠️ **ملاحظة مهمة:** يتضمن هذا الموضوع أحكامًا إسلامية دقيقة. "
            "المعلومات أعلاه مبنية على المصادر المسترجعة. "
            "للالتزامات الدينية الشخصية (الفرائض، الحرام، الحلال)، "
            "يرجى استشارة عالم إسلامي مؤهل يمكنه مراعاة ظروفك الخاصة."
        ),
        "ur": (
            "\n\n⚠️ **اہم نوٹ:** اس موضوع میں باریک اسلامی احکام شامل ہیں۔ "
            "اوپر دی گئی معلومات حاصل کردہ ذرائع پر مبنی ہیں۔ "
            "ذاتی مذہبی واجبات (فرائض، حرام، حلال) کے لیے، "
            "براہ کرم ایک مستند اسلامی عالم سے مشورہ کریں جو آپ کی مخصوص "
            "حالات پر غور کر سکے۔"
        ),
    },
    "connecting": {
        "en": "Connecting to backend…",
        "ar": "جاري الاتصال بالخادم…",
        "ur": "بیک اینڈ سے رابطہ کیا جا رہا ہے…",
    },
    "connected": {
        "en": "Connected to backend",
        "ar": "متصل بالخادم",
        "ur": "بیک اینڈ سے منسلک",
    },
    "disconnected": {
        "en": "Backend unavailable — using local knowledge",
        "ar": "الخادم غير متاح — استخدام المعرفة المحلية",
        "ur": "بیک اینڈ دستیاب نہیں — مقامی علم کا استعمال",
    },
    "generating": {
        "en": "Generating answer…",
        "ar": "جاري إنشاء الإجابة…",
        "ur": "جواب تیار کیا جا رہا ہے…",
    },
    "no_citations": {
        "en": "No citations found — using general knowledge",
        "ar": "لم يتم العثور على استشهادات — استخدام المعرفة العامة",
        "ur": "کوئی حوالے نہیں ملے — عام علم کا استعمال",
    },
    "cited_sources": {
        "en": "Cited — {n} source{s}",
        "ar": "مستشهد — {n} مصدر{s}",
        "ur": "حوالہ دیا گیا — {n} ذریعہ{s}",
    },
}


def get_ui_string(key: str, lang: str, **kwargs) -> str:
    """Get a UI string in the specified language."""
    entry = UI_STRINGS.get(key, {})
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


# ═══════════════════════════════════════════════
# TRANSLATION PROMPTS
# ═══════════════════════════════════════════════
TRANSLATE_SYSTEM_PROMPT = """\
You are a professional translator specializing in Islamic content.
Translate the given text from {source_lang} to {target_lang}.

Rules:
- Preserve the meaning and tone exactly
- Keep all citations in their original format (e.g., [Quran Al-Baqarah 2:153], [Bukhari 1469])
- Keep all Arabic Islamic terms in Arabic script (e.g., الله, القرآن, حديث, سنة)
- For Quran verses quoted in Arabic, keep the Arabic text as-is
- For Hadith references, keep the citation format unchanged
- Output ONLY the translated text — no explanations, no notes
- Maintain markdown formatting (bold, italic, lists)
"""


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    llm,
) -> str:
    """
    Translate text from source_lang to target_lang using the LLM.

    Args:
        text: The text to translate
        source_lang: Source language code (en, ar, ur)
        target_lang: Target language code (en, ar, ur)
        llm: The LLM instance to use for translation

    Returns:
        Translated text, or original text if translation fails or langs are the same.
    """
    # No translation needed
    if source_lang == target_lang:
        return text

    if not text or not text.strip():
        return text

    # Check cache
    cache_key = (hash(text), source_lang, target_lang)
    if cache_key in _translation_cache:
        logger.debug(f"Translation cache hit: {source_lang} → {target_lang}")
        return _translation_cache[cache_key]

    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    prompt = f"""{TRANSLATE_SYSTEM_PROMPT.format(source_lang=source_name, target_lang=target_name)}

Text to translate:
{text}

Translation:"""

    try:
        response = llm.invoke(prompt)
        translated = response.content if hasattr(response, "content") else str(response)
        translated = translated.strip()

        # Clean up common LLM artifacts
        if translated.startswith("```") and translated.endswith("```"):
            translated = translated[3:-3].strip()
        if translated.startswith('"') and translated.endswith('"'):
            translated = translated[1:-1].strip()

        # Cache the result
        if len(_translation_cache) >= _CACHE_MAX_SIZE:
            # Evict oldest entries (simple approach: clear half)
            keys = list(_translation_cache.keys())[:_CACHE_MAX_SIZE // 2]
            for k in keys:
                del _translation_cache[k]
        _translation_cache[cache_key] = translated

        logger.info(f"Translated {len(text)} chars: {source_lang} → {target_lang}")
        return translated

    except Exception as e:
        logger.error(f"Translation failed ({source_lang} → {target_lang}): {e}")
        return text  # Fallback to original


def translate_query_to_english(
    query: str,
    source_lang: str,
    llm,
) -> str:
    """
    Translate a user's query to English for vector search.
    The vector store has English content, so non-English queries must be translated first.
    """
    if source_lang == "en":
        return query
    return translate_text(query, source_lang, "en", llm)


def translate_response_to_language(
    response: str,
    target_lang: str,
    llm,
) -> str:
    """
    Translate an English response to the user's selected language.
    Preserves citations and Islamic terminology.
    """
    if target_lang == "en":
        return response
    return translate_text(response, "en", target_lang, llm)
