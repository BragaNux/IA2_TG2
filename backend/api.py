"""Backend HTTP (FastAPI): integra frontend, LLM (Claude) e servidor MCP.

Uso:  uvicorn backend.api:app --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.mcp_client import MCPToolClient
from backend.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Um único processo do servidor MCP (stdio) para toda a vida da API
    async with MCPToolClient() as mcp:
        state["mcp"] = mcp
        state["orchestrator"] = Orchestrator(mcp)
        logging.info("MCP conectado. Tools: %s", [t.name for t in mcp.tools])
        yield
    state.clear()


app = FastAPI(title="Assistente de Primeiros Socorros - RAG + MCP", lifespan=lifespan)


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    history: list[HistoryItem] = []


@app.get("/health")
async def health() -> dict:
    mcp: MCPToolClient = state["mcp"]
    return {"status": "ok", "mcp_tools": [t.name for t in mcp.tools], "model": state["orchestrator"].model}


@app.get("/topics")
async def topics() -> dict:
    rec = await state["mcp"].call("list_topics", {})
    if rec.is_error:
        raise HTTPException(502, rec.error)
    return rec.result


@app.get("/documents")
async def documents() -> dict:
    rec = await state["mcp"].call("list_documents", {})
    if rec.is_error:
        raise HTTPException(502, rec.error)
    return rec.result


@app.post("/chat")
async def chat(req: ChatRequest) -> dict:
    result = await state["orchestrator"].answer(req.message, [h.model_dump() for h in req.history])
    return result.to_dict()
