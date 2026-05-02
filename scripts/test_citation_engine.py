import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from src.utils.citation_engine import (
    extract_citations,
    format_citation_cards
)


def test_citation_extraction():
    sample_text = """
    Islam teaches patience in many places.
    [Quran Al-Baqarah 2:153]

    The Prophet said to fast on Mondays.
    [Bukhari, Book of Fasting, No. 1985]
    """

    citations = extract_citations(sample_text)

    print("\n=== RAW CITATIONS ===")
    for c in citations:
        print(c)

    print("\n=== FRONTEND CARDS ===")
    cards = format_citation_cards(citations)

    for card in cards:
        print(card)


if __name__ == "__main__":
    test_citation_extraction()
