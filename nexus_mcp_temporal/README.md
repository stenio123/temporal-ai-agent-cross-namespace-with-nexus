# Nexus-MCP Temporal - Bidirectional MCP ↔ Nexus Bridge

This project demonstrates the **nexus-mcp-python** bridge pattern, enabling bidirectional communication between MCP (Model Context Protocol) and Temporal Nexus operations.

## 🎯 What Makes This Different

Unlike the other three implementations, this project uses a **universal MCP Gateway** that acts as a bridge:

| Project | Pattern | Tool Access |
|---------|---------|-------------|
| **litellm_temporal** | Manual agent loop + Direct Nexus | Workflow → Nexus Operations |
| **openai_temporal** | OpenAI SDK + Direct Nexus | Workflow → Nexus Operations |
| **openai_temporal_mcp** | OpenAI SDK + MCP Servers | Workflow → MCP HTTP → Temporal |
| **nexus_mcp_temporal** | OpenAI SDK + Nexus-MCP Bridge | ↔ Gateway ↔ Nexus<br/>Workflow ↔ Gateway ↔ Nexus |

![Architecture](../images/nexus_mcp_temporal.png)

## 🚀 Quick Start

### Prerequisites

- **Temporal CLI**: `brew install temporal`
- **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **LLM API Key**: Set in `.env`
- **Python 3.13+**: Required by nexus-mcp-python

### Setup

```bash
cd nexus_mcp_temporal

# Install dependencies (includes nexus-mcp from git)
brew install protobuf
uv sync

# Start Temporal Server (separate terminal)
temporal server start-dev

# Create namespaces
temporal operator namespace create it-namespace
temporal operator namespace create finance-namespace

# Create Nexus endpoints
temporal operator nexus endpoint create \
    --name it-nexus-endpoint \
    --target-namespace it-namespace \
    --target-task-queue it-task-queue

temporal operator nexus endpoint create \
    --name finance-nexus-endpoint \
    --target-namespace finance-namespace \
    --target-task-queue finance-task-queue
```

### Start All Services

You need **5 terminal windows**:

```bash
# Terminal 1: IT MCP Gateway
uv run it_gateway_server.py

# Terminal 2: Finance MCP Gateway
uv run finance_gateway_server.py

# Terminal 3: Orchestrator Worker
uv run orchestrator_worker.py

# Terminal 4: IT Worker
uv run it_nexus_worker.py

# Terminal 5: Finance Worker
uv run finance_nexus_worker.py
```

### Run the Agent

```bash
# Terminal 6
uv run client.py
```

## Dynamic Tool Discovery Test

To test Finance tool refresh, follow the same process but:
1. Add a new tool to `app/finance_activities.py`
2. Update `app/finance_models.py`, `app/finance_service.py`, `app/finance_workflows.py`, `app/finance_nexus_handler.py`
3. Restart Finance gateway and worker
4. Send signal with `"Finance"` instead of `"IT"`:

```bash
temporal workflow signal \
  --workflow-id [WORKFLOW-ID] \
  --name refresh_mcp \
  --input '"Finance"'
```


## 📝 Sample Questions

Test all tools via the workflow:

**Local Tools**:
```
What is 125 * 8?
What's the weather like in Paris?
```

**IT Tools (via MCP Gateway)**:
```
What is my IP address?
Get JIRA metrics for project DEMO-456
```

**Finance Tools (via MCP Gateway)**:
```
Get stock price of TSLA
Calculate ROI for $10,000 at 5% over 10 years
```

## 🔄 Comparison with Other Projects

| Feature | openai_temporal | openai_temporal_mcp | nexus_mcp_temporal |
|---------|-----------------|---------------------|-------------------|
| **Tool Access** | Direct Nexus | HTTP MCP servers | MCP Gateway (WorkflowTransport) |
| **Transport** | Nexus RPC | HTTP (non-deterministic) | Nexus RPC (deterministic) |
| **External MCP Clients** | ❌ No | ❌ No | ✅ Yes |
| **Bidirectional** | ❌ No | ❌ No | ✅ Yes |
| **Universal Gateway** | ❌ No | ❌ No | ✅ Yes |
| **Dynamic Discovery** | ❌ No | ✅ Yes | ✅ Yes (via list_tools) |
| **SDK Integration** | ✅ Complete | ✅ Complete | ✅ Complete |
| **Nexus Observability** | ✅ Excellent | ❌ No | ✅ Excellent |
| **Workflow History** | ✅ Nexus operations | ⚠️ Activities only | ✅ Nexus operations |

## 🎯 Use Cases

**Best for**:
- **Deterministic MCP calls from workflows**: Tools must be replay-safe and tracked in history
- **Bidirectional tool access**: Both workflows AND external MCP clients need same tools
- **Universal tool registries**: Single gateway exposes all Nexus operations as MCP tools
- **Production observability**: Full Temporal tracking of all tool calls

**Choose openai_temporal instead when**:
- Simple direct Nexus calls without MCP abstraction
- No external MCP client requirements
- Prefer simpler architecture without gateway

**Choose openai_temporal_mcp instead when**:
- Standard MCP HTTP protocol is sufficient
- External MCP clients are primary consumers (not workflows)
- Deterministic replay not required for tool calls

## 📚 References

- [nexus-mcp-python GitHub](https://github.com/bergundy/nexus-mcp-python)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Temporal Nexus](https://docs.temporal.io/develop/python/nexus)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)

## ⚙️ Configuration Notes

### nexus-rpc Version
Uses `nexus-rpc==1.3.0`. The installed `nexusmcp` package requires a one-line fix in `.venv/lib/python3.14/site-packages/nexusmcp/service_handler.py:152`:
```python
# Change: service_defn.operations.values()
# To:     service_defn.operation_definitions.values()
```

This is due to API changes between nexus-rpc 1.1.0 (original) and 1.3.0 (current).
