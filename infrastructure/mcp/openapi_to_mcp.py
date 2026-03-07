"""OpenAPI → MCP Tool Auto-Generator.

Reads an OpenAPI spec (from a FastAPI service or JSON file) and generates
MCP tool definitions automatically. This reduces manual effort when adding
new endpoints to domain services.

Usage:
    # From a running FastAPI service:
    python -m infrastructure.mcp.openapi_to_mcp --url http://localhost:8001/openapi.json --output customer_tools.py

    # From a local file:
    python -m infrastructure.mcp.openapi_to_mcp --file openapi.json --output customer_tools.py

    # Programmatic:
    generator = OpenAPItoMCPGenerator()
    code = await generator.generate_from_url("http://localhost:8001/openapi.json")
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx


class OpenAPItoMCPGenerator:
    """Generates FastMCP tool definitions from OpenAPI specs."""

    def __init__(self, server_name: str = "service") -> None:
        self._server_name = server_name

    async def generate_from_url(self, url: str) -> str:
        """Fetch OpenAPI spec from URL and generate MCP tools."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            spec = resp.json()
        return self.generate(spec)

    def generate_from_file(self, path: str | Path) -> str:
        """Read OpenAPI spec from file and generate MCP tools."""
        with open(path) as f:
            spec = json.load(f)
        return self.generate(spec)

    def generate(self, spec: dict[str, Any]) -> str:
        """Generate MCP server code from an OpenAPI spec dict."""
        title = spec.get("info", {}).get("title", "Service")
        paths = spec.get("paths", {})

        lines = [
            f'"""Auto-generated MCP server from OpenAPI spec: {title}"""',
            "",
            "from __future__ import annotations",
            "",
            "import json",
            "from typing import Annotated",
            "",
            "import httpx",
            "from fastmcp import FastMCP",
            "",
            f'mcp = FastMCP("{title} MCP Server")',
            "",
            'BASE_URL = "http://localhost:8000"  # Update with actual service URL',
            "",
        ]

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                tool_code = self._generate_tool(path, method.upper(), operation)
                lines.append(tool_code)

        lines.extend(
            [
                "",
                'if __name__ == "__main__":',
                '    mcp.run(transport="stdio")',
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_tool(self, path: str, method: str, operation: dict[str, Any]) -> str:
        """Generate a single MCP tool from an OpenAPI operation."""
        operation_id = operation.get("operationId", "")
        summary = operation.get("summary", "")
        description = operation.get("description", summary)

        # Generate function name from operationId or path
        func_name = self._to_func_name(operation_id or path)

        # Extract parameters
        params = operation.get("parameters", [])
        path_params = [p for p in params if p.get("in") == "path"]
        query_params = [p for p in params if p.get("in") == "query"]

        # Extract request body
        request_body = operation.get("requestBody", {})
        body_schema = self._get_body_schema(request_body)

        # Build function signature
        sig_parts = []
        for p in path_params:
            ptype = self._schema_to_type(p.get("schema", {}))
            sig_parts.append(f'    {p["name"]}: Annotated[{ptype}, "{p.get("description", p["name"])}"],')
        for p in query_params:
            ptype = self._schema_to_type(p.get("schema", {}))
            default = p.get("schema", {}).get("default")
            default_str = f" = {repr(default)}" if default is not None else ""
            sig_parts.append(f'    {p["name"]}: Annotated[{ptype}, "{p.get("description", p["name"])}"]{default_str},')
        if body_schema:
            for prop_name, prop_info in body_schema.get("properties", {}).items():
                ptype = self._schema_to_type(prop_info)
                required = prop_name in body_schema.get("required", [])
                default_str = "" if required else " = None"
                desc = prop_info.get("description", prop_name)
                sig_parts.append(f'    {prop_name}: Annotated[{ptype}, "{desc}"]{default_str},')

        sig = "\n".join(sig_parts) if sig_parts else ""

        # Build URL with path params
        if "{" in path:
            url_expr = 'f"{BASE_URL}' + path + '"'
        else:
            url_expr = 'f"{BASE_URL}' + path + '"'

        # Build the tool function
        lines = [
            "",
            "@mcp.tool()",
            f"async def {func_name}(",
            sig,
            ") -> str:",
            f'    """{description}"""',
            "    async with httpx.AsyncClient(timeout=10.0) as client:",
        ]

        if method == "GET":
            qp_dict = ", ".join(f'"{p["name"]}": {p["name"]}' for p in query_params)
            qp_str = f", params={{{qp_dict}}}" if qp_dict else ""
            lines.append(f"        resp = await client.get({url_expr}{qp_str})")
        elif method in ("POST", "PUT", "PATCH"):
            if body_schema:
                body_fields = list(body_schema.get("properties", {}).keys())
                body_dict = ", ".join(f'"{f}": {f}' for f in body_fields)
                lines.append(f"        resp = await client.{method.lower()}({url_expr}, json={{{body_dict}}})")
            else:
                lines.append(f"        resp = await client.{method.lower()}({url_expr})")
        elif method == "DELETE":
            lines.append(f"        resp = await client.delete({url_expr})")

        lines.extend(
            [
                "        resp.raise_for_status()",
                "        return json.dumps(resp.json(), indent=2, ensure_ascii=False)",
            ]
        )

        return "\n".join(lines)

    def _to_func_name(self, text: str) -> str:
        """Convert operationId or path to a valid Python function name."""
        import re

        # Remove path separators and braces
        name = text.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_").lower()
        return name or "unknown_operation"

    def _schema_to_type(self, schema: dict[str, Any]) -> str:
        """Convert OpenAPI schema type to Python type hint."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_map.get(schema.get("type", "string"), "str")

    def _get_body_schema(self, request_body: dict[str, Any]) -> dict[str, Any] | None:
        """Extract schema from request body."""
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        return json_content.get("schema")


async def main():
    parser = argparse.ArgumentParser(description="Generate MCP tools from OpenAPI spec")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="URL to fetch OpenAPI spec from")
    group.add_argument("--file", help="Path to OpenAPI spec JSON file")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--name", default="service", help="Server name prefix")

    args = parser.parse_args()

    generator = OpenAPItoMCPGenerator(server_name=args.name)

    if args.url:
        code = await generator.generate_from_url(args.url)
    else:
        code = generator.generate_from_file(args.file)

    if args.output:
        Path(args.output).write_text(code)
        print(f"Generated MCP server → {args.output}")
    else:
        print(code)


if __name__ == "__main__":
    asyncio.run(main())
