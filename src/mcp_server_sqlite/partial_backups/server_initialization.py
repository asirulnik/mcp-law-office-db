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
        "--db-path", type=str, default="./database/mcp_server.db", help="Path to SQLite database file"
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

    # Create a separate logger for the application
    app_logger = logging.getLogger("mcp_law_office_server")
    app_logger.setLevel(numeric_level)

    # Run the server
    import asyncio
    asyncio.run(main(args.db_path))
