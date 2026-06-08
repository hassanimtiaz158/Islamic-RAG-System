from typing import TypedDict, Annotated, Dict, List
import operator


class IslamicAgentState(TypedDict):
    query: str
    query_type: str
    routing: list[str]

    retrieved_docs: Annotated[dict, operator.or_]

    context: str
    response: str
    citations: list
    citation_cards: list
    citation_valid: bool
    language: str
    iteration: int
