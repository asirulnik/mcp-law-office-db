#!/usr/bin/env python3

"""
Law Office SQLite MCP Server

A Model Context Protocol server implementation tailored for law office filing and billing.
This server provides specialized tools and resources for managing legal matters, client billing,
and invoice validation within a law practice.
"""

import os
import sys
import logging
from pathlib import Path
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
import asyncio

# Import our modules
from .database import SqliteDatabase
from .resource_handlers import handle_list_resources, handle_read_resource
from .tool_handlers import list_tools, handle_call_tool
from .prompt_handlers import list_prompts, handle_get_prompt

# reconfigure UnicodeEncodeError prone default (i.e. windows-1252) to utf-8
if sys.platform == "win32" and os.environ.get('PYTHONIOENCODING') is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger('mcp_law_office_server')
logger.info("Starting MCP Law Office SQLite Server")

async def main(db_path: str):
    """Main entry point for the Law Office SQLite MCP Server"""
    logger.info(f"Starting Law Office SQLite MCP Server with DB path: {db_path}")

    db = SqliteDatabase(db_path)
    server = Server("law-office-sqlite")

    # Register handlers
    logger.debug("Registering handlers")

    @server.list_resources()
    async def handle_list_resources_wrapper() -> list:
        """Wrapper for the list_resources handler"""
        return handle_list_resources()

    @server.read_resource()
    async def handle_read_resource_wrapper(uri: AnyUrl) -> str:
        """Wrapper for the read_resource handler"""
        return handle_read_resource(db, uri)

    @server.list_tools()
    async def handle_list_tools_wrapper() -> list:
        """Wrapper for the list_tools handler"""
        return list_tools()

    @server.call_tool()
    async def handle_call_tool_wrapper(name: str, arguments: dict | None) -> list:
        """Wrapper for the call_tool handler"""
        return handle_call_tool(db, name, arguments)

    @server.list_prompts()
    async def handle_list_prompts_wrapper() -> list:
        """Wrapper for the list_prompts handler"""
        return list_prompts()

    @server.get_prompt()
    async def handle_get_prompt_wrapper(name: str, arguments: dict | None) -> object:
        """Wrapper for the get_prompt handler"""
        return handle_get_prompt(db, name, arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Law Office Database Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="law-office-sqlite",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Law Office SQLite MCP Server")
    parser.add_argument(
        "--db-path", type=str, default="./database/law_office.db", help="Path to SQLite database file"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    args = parser.parse_args()

    # Configure logging
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Run the server
    asyncio.run(main(args.db_path))
