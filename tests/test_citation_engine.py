"""Regression tests for src/utils/citation_engine.py — the citation
extraction/verification logic behind the app's "zero-hallucination" guarantee.
"""

from src.utils.citation_engine import (
    check_islamic_safety,
    cross_reference_citations,
    extract_citations,
    verify_answer_grounding,
)


# ── extraction ──

def test_extract_quran_citation():
    citations = extract_citations('Patience is rewarded. [Quran Al-Baqarah 2:153]')
    assert len(citations) == 1
    c = citations[0]
    assert c["source"] == "quran"
    assert c["raw"] == "[Quran Al-Baqarah 2:153]"
    assert c["url"] == "https://quran.com/2/153"


def test_extract_hadith_compact_citation():
    citations = extract_citations('The Prophet said this. [Bukhari 1469]')
    assert len(citations) == 1
    assert citations[0]["source"] == "bukhari"
    assert citations[0]["url"] == "https://sunnah.com/bukhari:1469"


def test_extract_hadith_verbose_citation():
    citations = extract_citations('[Bukhari, Book of Fasting, No. 1985]')
    assert len(citations) == 1
    assert citations[0]["source"] == "bukhari"
    assert citations[0]["reference"] == "Bukhari 1985"


def test_extract_multiple_citations_no_duplicates_lost():
    text = 'A. [Quran Al-Baqarah 2:153] B. [Bukhari 1469] C. [Muslim 2999]'
    citations = extract_citations(text)
    sources = sorted(c["source"] for c in citations)
    assert sources == ["bukhari", "muslim", "quran"]


def test_extract_no_citations():
    assert extract_citations("Just a plain sentence with no brackets.") == []


# ── Arabic/Urdu citations stay in the fixed English bracket format ──
# (regression test for the bug where LANGUAGE_INSTRUCTIONS told the LLM to
# translate citation brackets into Arabic/Urdu, making them invisible to
# extraction and causing every non-English answer to be flagged as ungrounded)

def test_arabic_response_with_english_citation_brackets_is_extracted():
    response = 'الصبر فضيلة عظيمة في الإسلام. [Quran Al-Baqarah 2:153]'
    citations = extract_citations(response)
    assert len(citations) == 1
    assert citations[0]["source"] == "quran"


def test_urdu_response_with_english_citation_brackets_is_extracted():
    response = 'صبر اسلام میں ایک عظیم فضیلت ہے۔ [Bukhari 1469]'
    citations = extract_citations(response)
    assert len(citations) == 1
    assert citations[0]["source"] == "bukhari"


# ── grounding ──

def test_grounding_fails_with_no_citations():
    is_grounded, unsupported, confidence = verify_answer_grounding(
        "Some answer with no citations at all here.", context="", citations=[]
    )
    assert is_grounded is False
    assert confidence < 0.5
    assert unsupported


def test_grounding_passes_when_citation_matches_context():
    context = "[QURAN] Al-Baqarah 2:153\nO you who believe, seek help through patience and prayer."
    response = 'Seek help through patience and prayer. [Quran Al-Baqarah 2:153]'
    citations = extract_citations(response)
    is_grounded, unsupported, confidence = verify_answer_grounding(response, context, citations)
    assert is_grounded is True
    assert confidence >= 0.5


def test_grounding_flags_citation_not_in_context():
    context = "Unrelated retrieved text with nothing matching."
    response = 'A fabricated claim. [Quran Al-Baqarah 2:153]'
    citations = extract_citations(response)
    is_grounded, unsupported, confidence = verify_answer_grounding(response, context, citations)
    assert any("not found in retrieved sources" in u for u in unsupported)


def test_sentence_splitter_does_not_fragment_on_verse_number():
    # "2:153." should not be treated as a sentence boundary just because of
    # the trailing period on the citation's verse number — otherwise the claim
    # text gets split away from its own citation and is wrongly flagged uncited.
    context = "[QURAN] Al-Baqarah 2:153\nSeek help through patience and prayer."
    response = 'Seek help through patience and prayer, as stated in verse 2:153. [Quran Al-Baqarah 2:153]'
    citations = extract_citations(response)
    _, unsupported, _ = verify_answer_grounding(response, context, citations)
    uncited = [u for u in unsupported if u.startswith("Uncited claim")]
    assert not uncited


# ── safety flags ──

def test_safety_flags_unattributed_scholarly_opinion():
    flags = check_islamic_safety("It is permissible to do this according to scholars.", citations=[])
    assert "scholarly_opinion_without_sources" in flags


def test_safety_no_flag_when_citations_present():
    citations = extract_citations("[Bukhari 1469]")
    flags = check_islamic_safety("It is obligatory, per this source. [Bukhari 1469]", citations)
    assert "scholarly_opinion_without_sources" not in flags


def test_safety_flags_sensitive_topic():
    flags = check_islamic_safety("This concerns divorce and inheritance rulings.", citations=[])
    assert "sensitive_topic" in flags


# ── cross-reference / hallucination ratio ──

def test_cross_reference_verified_citation():
    context = "[QURAN] Al-Baqarah 2:153\nSeek help through patience and prayer."
    citations = extract_citations('[Quran Al-Baqarah 2:153]')
    verdicts, ratio, passed = cross_reference_citations("...", context, citations)
    assert verdicts[0]["verified"] is True
    assert ratio == 0.0
    assert passed is True


def test_cross_reference_unverified_citation():
    context = "Completely unrelated context text."
    citations = extract_citations('[Quran Al-Baqarah 2:153]')
    verdicts, ratio, passed = cross_reference_citations("...", context, citations)
    assert verdicts[0]["verified"] is False
    assert ratio == 1.0
    assert passed is False


def test_cross_reference_unknown_source_is_neutral_not_auto_verified():
    # A citation whose source couldn't be classified must not silently count
    # as "verified" (that would let malformed/unparseable citations inflate
    # the hallucination ratio's trustworthiness).
    citations = [{"raw": "[Something 1]", "source": "unknown", "reference": "Something 1"}]
    verdicts, ratio, passed = cross_reference_citations("...", "any context", citations)
    assert verdicts[0]["verified"] is False
    assert verdicts[0]["unverifiable"] is True
    # Excluded from the ratio entirely (neutral), same as having no citations.
    assert ratio == 0.0
    assert passed is True
