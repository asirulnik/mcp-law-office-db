"""
Law Office SQLite MCP Server

A Model Context Protocol server implementation tailored for law office filing and billing.
This server provides specialized tools and resources for managing legal matters, client billing,
and invoice validation within a law practice.
"""

import sys
import asyncio
import argparse
import logging

__version__ = "1.0.0"

from .server_law_office import main as _main

def main():
    """Main entry point for the Law Office SQLite MCP Server when run as a module"""
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
    asyncio.run(_main(args.db_path))

__all__ = ["main", "_main"]
