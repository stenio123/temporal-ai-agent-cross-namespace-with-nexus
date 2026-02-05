"""
Shared constants for the MCP HTTP integration demo.
Update these values if using different namespace IDs or MCP server ports.
"""
import os

# Namespace IDs
NAMESPACE_IT = "it-namespace"
NAMESPACE_FINANCE = "finance-namespace"

# Task Queue Names
QUEUE_ORCHESTRATOR = "orchestrator-queue"
QUEUE_IT = "it-tools-queue"
QUEUE_FINANCE = "finance-tools-queue"

# Temporal Server Address
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

# MCP Transport Configuration
MCP_DEFAULT_HOST = "0.0.0.0"

# MCP Server Configuration
# Add new MCP servers here - they'll automatically be available to the agent
MCP_SERVERS = [
    {
        "name": "finance",
        "url": f"http://localhost:{os.getenv('FINANCE_MCP_PORT', '8001')}/mcp",
        "port": int(os.getenv("FINANCE_MCP_PORT", "8001")),
        "host": os.getenv("MCP_HOST", MCP_DEFAULT_HOST),
        "description": "Financial operations like stock prices and investment calculations. Tools: stock_price, calculate_roi"
    },
    {
        "name": "it",
        "url": f"http://localhost:{os.getenv('IT_MCP_PORT', '8002')}/mcp",
        "port": int(os.getenv("IT_MCP_PORT", "8002")),
        "host": os.getenv("MCP_HOST", MCP_DEFAULT_HOST),
        "description": "IT operations like JIRA metrics and IP lookup. Tools: get_ip, get_jira_metrics"
    },
]
