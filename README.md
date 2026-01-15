# Cross Namespace AI Agent Orchestration with Temporal Nexus

## 🚀 Quick Start

```bash
# 1. Install Temporal CLI
brew install temporal  # macOS
# or: curl -sSf https://temporal.download/cli.sh | sh  # Linux

# 2. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set your LLM API key
export OPENAI_API_KEY='sk-your-key-here'

# 4. Install dependencies
cd /path/to/researchPaper/code
uv sync

# 5. Start Temporal (in separate terminal)
temporal server start-dev

# 6. Start worker (in another terminal)
uv run worker.py

# 7. Run the agent (in third terminal)
uv run start_workflow.py
```

### Create Namespace in local dev
```
temporal operator namespace create it-namespace
temporal operator namespace create finance-namespace
```

### Create Nexus Endpoints
```
temporal operator nexus endpoint create \
    --name it-nexus-endpoint \
    --target-namespace it-namespace \
    --target-task-queue it-task-queue
temporal operator nexus endpoint create \
    --name finance-nexus-endpoint \
    --target-namespace finance-namespace \
    --target-task-queue finance-task-queue

```
### Create Namespace in Temporal Cloud
```
cd infrastructure
terraform apply
# Make sure to update the namespace in the it_nexus_worker.py and the finance_nexus_worker.py file
```


---

## Architecture Overview

### Stage 2: Cross-Namespace Architecture with Temporal Nexus

```
┌────────────────────────────────────────────────────────────────┐
│                     Orchestrator Workflow                       │
│                    (default namespace)                          │
│  • Manages durable agent loop (while True)                     │
│  • Calls Nexus operations for remote tools (deterministic!)    │
│  • Calls activities for local tools & LLM                      │
└──────┬──────────────────────────────────┬──────────────────────┘
       │                                  │
       │ Nexus Operations                 │ Activities
       │ (Cross-namespace)                │ (Same namespace)
       │                                  │
       ▼                                  ▼
┌─────────────────┐              ┌──────────────────┐
│  Temporal       │              │ plan_next_action │
│  Nexus          │              │  execute_tool    │
│  Endpoints      │              │  (LLM, calc, etc)│
└───┬─────────┬───┘              └──────────────────┘
    │         │
    │         │
    ▼         ▼
┌──────────────────┐    ┌──────────────────────┐
│  IT Namespace    │    │  Finance Namespace   │
│                  │    │                      │
│ ┌──────────────┐ │    │ ┌──────────────────┐│
│ │ Nexus Handler│ │    │ │  Nexus Handler   ││
│ │              │ │    │ │                  ││
│ │ • list_tools │ │    │ │  • list_tools    ││
│ │ • execute_   │ │    │ │  • execute_tool  ││
│ │   tool       │ │    │ │                  ││
│ └──────┬───────┘ │    │ └────────┬─────────┘│
│        │         │    │          │          │
│        ▼         │    │          ▼          │
│ ┌──────────────┐ │    │ ┌──────────────────┐│
│ │IT Activities │ │    │ │Finance Activities││
│ │• jira_metrics│ │    │ │• stock_price     ││
│ │• get_ip      │ │    │ │• calculate_roi   ││
│ └──────────────┘ │    │ └──────────────────┘│
└──────────────────┘    └──────────────────────┘
```

### Key Architectural Decisions

#### ✅ Nexus Calls from Workflow (Not Activities)

**Why:** The Python SDK [explicitly states](https://github.com/temporalio/sdk-python):
> "There is no support currently for calling a Nexus operation from non-workflow code."

**Solution:** Nexus calls are made directly from the workflow:
- `_discover_remote_tools()` - Calls Nexus to list available tools
- `_execute_nexus_tool()` - Calls Nexus to execute remote tools

**Determinism:** Nexus calls from workflows ARE deterministic:
- Results are recorded in workflow history
- On replay, Temporal uses recorded results (doesn't re-execute)
- Same as how activities work

#### ⚠️ Demo Trade-off: Synchronous Nexus Operations

**Current Implementation:**
```python
@nexusrpc.handler.sync_operation
async def execute_tool(self, ctx, input):
    # Calls activity methods as regular Python functions
    activities = ITActivities()
    result = await activities.jira_metrics(...)
    return result
```

**Trade-offs:**
- ✅ Simple and works for fast operations (< 10s)
- ✅ Good for demo purposes
- ❌ **No automatic retries** if function fails
- ❌ **No Temporal activity features** (heartbeats, timeouts, etc.)
- ❌ **Not durable** - if the Nexus handler crashes, work is lost

**Production Recommendation:**

For production use, Nexus handlers should start workflows instead:

```python
@nexus.workflow_run_operation
async def execute_tool(
    self,
    ctx: nexus.WorkflowRunOperationContext,
    input: Dict
) -> nexus.WorkflowHandle[Dict]:
    # Start a REAL workflow that properly calls activities
    return await ctx.start_workflow(
        ITToolWorkflow.run,
        input,
        id=f"it-tool-{uuid.uuid4()}",
    )
```

This provides:
- ✅ Full Temporal durability and retry logic
- ✅ Proper activity execution with history
- ✅ Better observability and debugging
- ⚠️ More complex setup (need workflows in IT/Finance namespaces)

### What's Durable vs Not Durable

| Component | Durable? | Explanation |
|-----------|----------|-------------|
| Orchestrator workflow | ✅ Yes | Full Temporal workflow with history |
| Orchestrator activities (LLM, local tools) | ✅ Yes | Proper activities with retries |
| Nexus calls (to IT/Finance) | ✅ Yes | Results recorded in orchestrator history |
| **IT/Finance tool execution** | ❌ **No** | Called as Python functions, not Temporal activities |

**Impact:** If an IT/Finance tool fails during execution, there's no automatic retry. The orchestrator sees the failure and can retry the entire Nexus call, but the individual tool execution isn't durable.

**For this demo:** This is acceptable - we're demonstrating cross-namespace communication, not production-grade durability.

Execution flow:

![Alt Text](images/execution_flow.png)


## Prerequisites

1. **Temporal CLI**: Install the Temporal CLI for running the dev server
   ```bash
   # On macOS:
   brew install temporal
   
   # On Linux:
   curl -sSf https://temporal.download/cli.sh | sh
   
   # For other platforms, see: https://docs.temporal.io/cli
   ```

2. **uv**: Fast Python package installer and manager
   ```bash
   # On macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or via pip:
   pip install uv
   ```

3. **Python 3.8+**: Managed automatically by `uv`

4. **LLM API Key**: You'll need an API key for your LLM provider

## Installation

### 1. Set up your LLM API Key

- Make a copy of .env.example and name it .env 
- Choose your provider and set the appropriate environment variable

### 2. Install Dependencies

```bash
# Create virtual environment and install dependencies
uv sync

# This will:
# - Create a .venv directory with a virtual environment
# - Install all dependencies from pyproject.toml
# - Lock dependencies in uv.lock for reproducibility
```

### 3. Start Temporal Dev Server

In a **separate terminal** (keep it running):

```bash
# Start Temporal development server
temporal server start-dev

# This will:
# - Start Temporal server on localhost:7233
# - Start Web UI on http://localhost:8233
# - Use in-memory database
```

**Verify Temporal is running:**
- Open http://localhost:8233 in your browser
- You should see the Temporal Web UI

## Running the Agent

**Prerequisites:** Make sure you have:
1. ✅ Set your LLM API key environment variable
2. ✅ Temporal dev server running (`temporal server start-dev`)
3. ✅ Installed dependencies (`uv sync`)

### 1. Start the Worker

In one terminal:
```bash
uv run worker.py
```

This starts the Temporal worker that executes workflows and activities.

### 2. Start an Interactive Session

In **another terminal** (keep the worker running):
```bash
uv run start_workflow.py
```

You can now chat with the agent. Try these examples:
- "What is 25 + 17?"
- "What's the weather in Seattle?"
- "Calculate 100 / 5"

Type `quit`, `exit`, or `bye` to end the session.


## Note
This implementation is for educational purposes only and is not intended to be used in production. Current limitations include no context window management and no session management.