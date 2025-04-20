"""
Law Office SQLite MCP Server

A Model Context Protocol server implementation tailored for law office filing and billing.
This server provides specialized tools and resources for managing legal matters, client billing,
and invoice validation within a law practice.
"""

__version__ = "1.0.0"

from .server_law_office import main

__all__ = ["main"]
