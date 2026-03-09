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
import inspect
import logging
import typing
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

# MCP server registry — maps server name to module path
MCP_SERVER_REGISTRY: dict[str, str] = {
    "customer": "infrastructure.mcp.customer_mcp_server",
    "billing": "infrastructure.mcp.billing_mcp_server",
    "network": "infrastructure.mcp.network_mcp_server",
    "campaign": "infrastructure.mcp.campaign_mcp_server",
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
                    len(tools),
                    server_name,
                )
            except Exception:
                logger.exception("Failed to discover tools from '%s'", server_name)

        return self._tools

    async def _discover_from_module(self, server_name: str, module_path: str) -> list[StructuredTool]:
        """Import an MCP server module and extract its tools."""
        import importlib

        module = importlib.import_module(module_path)
        mcp_server = getattr(module, "mcp", None)

        if mcp_server is None:
            logger.warning("No 'mcp' object found in %s", module_path)
            return []

        tools: list[StructuredTool] = []

        # FastMCP stores tools in _tool_manager.tools (dict of MCPTool)
        # Try multiple access paths for compatibility across FastMCP versions
        tool_dict = _extract_tool_dict(mcp_server)
        if tool_dict is None:
            logger.warning("Could not extract tools from MCP server '%s'", server_name)
            return []

        for tool_name, tool_info in tool_dict.items():
            fn = tool_info.fn if hasattr(tool_info, "fn") else tool_info
            description = ""
            if hasattr(tool_info, "description") and tool_info.description:
                description = tool_info.description
            elif fn.__doc__:
                description = fn.__doc__
            else:
                description = f"MCP tool: {tool_name}"

            # Build a Pydantic model from the tool's parameters
            input_schema = _build_input_schema(tool_name, fn)

            # Create a proper closure to avoid late-binding issues
            lc_tool = _make_langchain_tool(tool_name, description, fn, input_schema)
            tools.append(lc_tool)

        return tools

    def get_tool_names(self) -> list[str]:
        """Return names of all discovered tools."""
        return [t.name for t in self._tools]

    def get_tool_count(self) -> int:
        """Return total number of discovered tools."""
        return len(self._tools)


def _extract_tool_dict(mcp_server: Any) -> dict[str, Any] | None:
    """Extract the tool dictionary from a FastMCP server across versions."""
    # FastMCP >= 2.x: mcp._tool_manager._tools
    tool_manager = getattr(mcp_server, "_tool_manager", None)
    if tool_manager is not None:
        tools_attr = getattr(tool_manager, "_tools", None) or getattr(tool_manager, "tools", None)
        if tools_attr and isinstance(tools_attr, dict):
            return tools_attr

    # FastMCP with _local_provider
    local_provider = getattr(mcp_server, "_local_provider", None)
    if local_provider is not None:
        components = getattr(local_provider, "_components", None)
        if components and isinstance(components, dict):
            # Filter for tool components
            return {k: v for k, v in components.items() if hasattr(v, "fn")}

    # Fallback: try _tools directly
    direct_tools = getattr(mcp_server, "_tools", None)
    if direct_tools and isinstance(direct_tools, dict):
        return direct_tools

    return None


def _make_langchain_tool(
    tool_name: str,
    description: str,
    fn: Any,
    input_schema: type[BaseModel],
) -> StructuredTool:
    """Create a LangChain StructuredTool wrapping an MCP tool function.

    Uses a factory function to avoid closure late-binding issues.
    Tool names are kept as-is (no server prefix) to match agent prompts.
    """
    captured_fn = fn

    async def _invoke(**kwargs: Any) -> str:
        result = captured_fn(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return str(result)

    return StructuredTool(
        name=tool_name,
        description=description,
        func=lambda **_kwargs: None,
        coroutine=_invoke,
        args_schema=input_schema,
    )


def _build_input_schema(tool_name: str, fn: Any) -> type[BaseModel]:
    """Build a Pydantic model from a tool function's signature."""
    sig = inspect.signature(fn)
    fields: dict[str, Any] = {}

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        annotation = param.annotation if param.annotation != inspect.Parameter.empty else str

        # Unwrap Annotated types
        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            args = typing.get_args(annotation)
            base_type = args[0] if args else str
            desc = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
        else:
            base_type = annotation
            desc = ""

        # Handle Optional (Union[X, None])
        if typing.get_origin(base_type) is typing.Union:
            union_args = typing.get_args(base_type)
            non_none = [a for a in union_args if a is not type(None)]
            base_type = non_none[0] if non_none else str

        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[param_name] = (base_type, Field(default=default, description=desc))

    model_name = f"{tool_name.title().replace('_', '')}Input"
    return create_model(model_name, **fields)
