from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import asyncio

# Your graph import (adjust if needed)
from src.agents.islamic_graph import build_islamic_graph
from src.core.islamic_vectorDB import IslamicVectorStore


# =========================
# APP SETUP
# =========================
app = FastAPI(
    title="Islamic Knowledge RAG API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend (optional)
app.mount(
    "/app",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)


# =========================
# GLOBAL GRAPH (IMPORTANT)
# =========================
vector_store = IslamicVectorStore()
graph = build_islamic_graph(vector_store)


# =========================
# REQUEST MODEL
# =========================
class QueryRequest(BaseModel):
    query: str
    language: str = "en"
    sources: list[str] = []


# =========================
# REST API ENDPOINT
# =========================
@app.post("/api/ask")
async def ask_islamic(req: QueryRequest):

    result = graph.invoke({
        "query": req.query,
        "language": req.language,
        "retrieved_docs": {},
        "iteration": 0,
    })

    return {
        "answer": result.get("response", ""),
        "citations": result.get("citations", []),
        "citation_cards": result.get("citation_cards", []),
        "citation_valid": result.get("citation_valid", False),
        "sources_used": list(result.get("retrieved_docs", {}).keys()),
    }


# =========================
# WEBSOCKET STREAMING API
# =========================
@app.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    await ws.accept()

    while True:
        data = await ws.receive_json()

        async for event in graph.astream_events(
            {
                "query": data["query"],
                "retrieved_docs": {},
                "iteration": 0,
            },
            version="v2"
        ):
            if event["event"] == "on_llm_stream":
                await ws.send_json({
                    "type": "token",
                    "content": event["data"]["chunk"]
                })

            elif event["event"] == "on_chain_end":
                await ws.send_json({
                    "type": "done",
                    "citations": []
                })


# =========================
# CITATION VERIFICATION API
# =========================
@app.get("/api/verify-citation")
async def verify_citation(surah: int, ayah: int):

    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.yusufali"
    resp = requests.get(url)

    if resp.status_code == 200:
        data = resp.json()["data"]

        return {
            "verified": True,
            "text": data["text"],
            "surah": data["surah"]["englishName"],
        }

    return {
        "verified": False,
        "error": "Verse not found"
    }
