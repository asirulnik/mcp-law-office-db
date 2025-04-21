# setup.py
from setuptools import setup, find_packages

setup(
    name="mcp-server-law-office", # Or maybe "mcp-law-office-db" - adjust if needed
    version="1.0.0", # Use your project's version
    packages=find_packages("src"),
    package_dir={"": "src"},
    # Dependencies are usually listed here OR in requirements.txt / pyproject.toml
    # Since we installed them already, we can leave install_requires empty or remove it
    # install_requires=[
    #     "mcp>=1.6.0", # Example, use actual version if known/needed
    #     "pydantic>=2.0.0",
    # ],
    entry_points={
        "console_scripts": [
            # This defines how the server might be run if installed globally,
            # but isn't strictly necessary for Claude Desktop use via direct path.
            # Adjust the entry point if needed, or remove if unused.
            "mcp-server-law-office=mcp_server_sqlite.server_law_office:main",
        ],
    },
    python_requires=">=3.10", # Match the dependency requirement
    author="Law Office Development Team", # Or your name
    author_email="example@example.com", # Or your email
    description="SQLite MCP Server for Law Office Filing and Billing",
    keywords="mcp, law, billing, legal, filing",
    project_urls={
        "MCP Docs": "https://modelcontextprotocol.io",
    },
)