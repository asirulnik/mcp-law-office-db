#!/usr/bin/env python3

"""
Law Office SQLite MCP Server Runner

This script starts the Law Office SQLite MCP Server with the specified database path.
It handles command-line arguments and configures logging.
"""

import sys
import os
import asyncio
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger("law_office_mcp_runner")

def main():
    """Main entry point for the Law Office SQLite MCP Server"""
    parser = argparse.ArgumentParser(description="Law Office SQLite MCP Server")
    parser.add_argument(
        "--db-path", type=str, default="./database/law_office.db", 
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO", 
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    args = parser.parse_args()

    # Configure logging level
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")
    
    logging.getLogger().setLevel(numeric_level)

    # Add src directory to Python path if running directly
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    if os.path.exists(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
        logger.info(f"Added {src_dir} to Python path")

    # Try multiple import approaches to handle different installation scenarios
    try:
        # First try normal import (if installed as a package)
        try:
            from mcp_server_sqlite.server_law_office import main as server_main
            logger.info("Imported server from installed package")
        except ImportError:
            # Try direct import if running from source directory
            try:
                from src.mcp_server_sqlite.server_law_office import main as server_main
                logger.info("Imported server from src directory")
            except ImportError:
                # Last resort, try to import from current directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
                from mcp_server_sqlite.server_law_office import main as server_main
                logger.info("Imported server from current directory")
        
        # Run the server
        db_path = os.path.abspath(args.db_path)
        logger.info(f"Starting Law Office SQLite MCP Server with database: {db_path}")
        asyncio.run(server_main(db_path))
        
    except ImportError as e:
        logger.error(f"Failed to import server module: {e}")
        logger.error("Python path: %s", sys.path)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
