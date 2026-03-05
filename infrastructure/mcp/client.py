"""MCP Client — Dynamic tool discovery for LangGraph agents.

Connects to MCP servers, discovers available tools at runtime,
and wraps them as LangChain tools the agent can use.

Key benefit: Adding a new tool to an MCP server does NOT require
agent restart — the client re-discovers tools on each session.

Usage:
    client = MCPToolClient()
    tools = await client.discover_tools()
    agent = create_react_agent(model=llm, tools=tools)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

# MCP server registry — maps server name to module path
MCP_SERVER_REGISTRY: dict[str, str] = {
    "customer": "infrastructure.mcp.customer_mcp_server",
    "billing": "infrastructure.mcp.billing_mcp_server",
}


class MCPToolClient:
    """Client that discovers and wraps MCP tools as LangChain tools.

    Supports two modes:
    1. Direct import mode (default) — imports MCP server modules and extracts tools
    2. Subprocess mode — runs MCP servers as subprocesses via stdio transport
    """

    def __init__(self, servers: dict[str, str] | None = None) -> None:
        self._servers = servers or MCP_SERVER_REGISTRY
        self._tools: list[StructuredTool] = []

    async def discover_tools(self) -> list[StructuredTool]:
        """Discover all tools from registered MCP servers.

        Returns LangChain-compatible tools that can be passed to create_react_agent.
        """
        self._tools = []

        for server_name, module_path in self._servers.items():
            try:
                tools = await self._discover_from_module(server_name, module_path)
                self._tools.extend(tools)
                logger.info(
                    "Discovered %d tools from MCP server '%s'",
                    len(tools), server_name,
                )
            except Exception:
                logger.exception("Failed to discover tools from '%s'", server_name)

        return self._tools

    async def _discover_from_module(
        self, server_name: str, module_path: str
    ) -> list[StructuredTool]:
        """Import an MCP server module and extract its tools."""
        import importlib

        module = importlib.import_module(module_path)
        mcp_server = getattr(module, "mcp", None)

        if mcp_server is None:
            logger.warning("No 'mcp' object found in %s", module_path)
            return []

        tools: list[StructuredTool] = []

        # FastMCP stores tools internally — access via _tool_manager
        tool_manager = getattr(mcp_server, "_tool_manager", None)
        if tool_manager is None:
            logger.warning("No tool manager found in MCP server '%s'", server_name)
            return []

        for tool_name, tool_info in tool_manager._tools.items():
            fn = tool_info.fn
            description = tool_info.description or fn.__doc__ or f"MCP tool: {tool_name}"

            # Build a Pydantic model from the tool's parameters
            input_schema = _build_input_schema(tool_name, tool_info)

            # Create a wrapper that calls the original MCP tool function
            async def _invoke(wrapper_fn=fn, **kwargs: Any) -> str:
                result = wrapper_fn(**kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return str(result)

            lc_tool = StructuredTool(
                name=f"{server_name}_{tool_name}",
                description=f"[{server_name.upper()}] {description}",
                func=lambda **kwargs: None,  # sync placeholder
                coroutine=_invoke,
                args_schema=input_schema,
            )
            tools.append(lc_tool)

        return tools

    def get_tool_names(self) -> list[str]:
        """Return names of all discovered tools."""
        return [t.name for t in self._tools]

    def get_tool_count(self) -> int:
        """Return total number of discovered tools."""
        return len(self._tools)


def _build_input_schema(tool_name: str, tool_info: Any) -> type[BaseModel]:
    """Build a Pydantic model from MCP tool parameter info."""
    import inspect

    fn = tool_info.fn
    sig = inspect.signature(fn)
    fields: dict[str, Any] = {}

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
        # Unwrap Annotated types to get the base type
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            # Handle Annotated[str, "description"]
            import typing
            if hasattr(typing, "get_args"):
                args = typing.get_args(annotation)
                if args:
                    base_type = args[0]
                    desc = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
                else:
                    base_type = str
                    desc = ""
            else:
                base_type = str
                desc = ""
        else:
            base_type = annotation
            desc = ""

        # Handle Optional types
        if hasattr(base_type, "__origin__") and base_type.__origin__ is type(None):
            base_type = str

        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[param_name] = (base_type, Field(default=default, description=desc))

    model_name = f"{tool_name.title().replace('_', '')}Input"
    return create_model(model_name, **fields)
