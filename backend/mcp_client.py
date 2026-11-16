"""Cliente MCP: sobe o servidor (stdio), descobre as tools e as executa via protocolo MCP.

O backend NÃO importa as funções do servidor: toda chamada passa por JSON-RPC
(session.call_tool), exatamente como faria qualquer outro cliente MCP.
"""
from __future__ import annotations

import json
import os
import sys
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from rag.config import ROOT_DIR


@dataclass
class ToolCallRecord:
    """Registro de uma chamada de tool (exibido na interface como evidência)."""
    name: str
    arguments: dict
    duration_ms: float
    is_error: bool
    result: dict | None
    error: str | None = None


class MCPToolClient:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self.tools: list = []

    async def __aenter__(self) -> "MCPToolClient":
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=str(ROOT_DIR),
            env={**os.environ, "PYTHONPATH": str(ROOT_DIR), "PYTHONIOENCODING": "utf-8"},
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        self.tools = (await self.session.list_tools()).tools
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    def anthropic_tools(self) -> list[dict]:
        """Converte as tools descobertas via MCP para o formato de tool use da API do Claude."""
        return [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in self.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        assert self.session is not None, "MCPToolClient não inicializado"
        t0 = time.perf_counter()
        try:
            res = await self.session.call_tool(name, arguments)
        except Exception as e:  # falha de transporte/protocolo
            return ToolCallRecord(name, arguments, (time.perf_counter() - t0) * 1000, True, None, str(e))
        ms = (time.perf_counter() - t0) * 1000
        text = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
        if res.isError:
            return ToolCallRecord(name, arguments, ms, True, None, text or "erro na tool")
        data = res.structuredContent
        if data is None:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                data = {"text": text}
        return ToolCallRecord(name, arguments, ms, False, data)
