# Cross Namespace AI Agent Orchestration with Temporal Nexus

## 🚀 Quick Start

### 1. Prerequisites
*   **Temporal CLI**: `brew install temporal` (macOS)
*   **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
*   **LLM API Key**: Copy `.env.example` to `.env` and add your `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

### 2. Setup Environment
```bash
# Install dependencies
uv sync

# Start Temporal Server (in a separate terminal)
temporal server start-dev

# Create Namespaces (local dev only)
temporal operator namespace create it-namespace
temporal operator namespace create finance-namespace

# Create Nexus Endpoints (local dev only)
temporal operator nexus endpoint create \
    --name it-nexus-endpoint \
    --target-namespace it-namespace \
    --target-task-queue it-task-queue

temporal operator nexus endpoint create \
    --name finance-nexus-endpoint \
    --target-namespace finance-namespace \
    --target-task-queue finance-task-queue
```

### 3. Start Workers (Run each in a separate terminal)
```bash
# Start the Orchestrator (default namespace)
uv run orchestrator_worker.py

# Start the IT Worker (it-namespace)
uv run it_nexus_worker.py

# Start the Finance Worker (finance-namespace)
uv run finance_nexus_worker.py
```

### 4. Run the Agent
```bash
uv run start_workflow.py
```

---

## 💬 Sample Questions to Ask

Try these examples to see the cross-namespace orchestration in action:

1.  **Local Tool (Orchestrator)**:
    *   "What is 125 * 8?"
    *   "What's the weather like in New York?"
2.  **Remote IT Tool**:
    *   "What is the IP address of this computer?"
    *   "Get JIRA metrics for project PROJ-123"
3.  **Remote Finance Tool**:
    *   "What is the stock price of AAPL?"
    *   "Calculate ROI for $10,000 at 7% over 5 years"

---

## 🔍 Validation and Observability

To confirm the cross-namespace communication is working as expected:

1.  **Temporal Web UI**:
    *   Open `http://localhost:8233`
    *   Find your `OrchestratorWorkflow` execution.
    *   In the **Nexus** tab, you can see the outgoing Nexus operations to `it-nexus-endpoint` and `finance-nexus-endpoint`.
    *   Notice how the results are recorded in the workflow history.
2.  **Worker Terminal Logs**:
    *   Check the **IT Worker** terminal to see when `jira_metrics` or `get_ip` are triggered.
    *   Check the **Finance Worker** terminal to see `stock_price` or `calculate_roi` executions.
    *   Observe that the Orchestrator worker discovers tools from both namespaces on startup.

---

### Temporal Cloud (optional)
If you want to use Temporal Cloud instead of a local environment, you can create the Namespaces and Nexus endpoints using Terraform:
```bash
cd infrastructure
terraform apply
# Make sure to update app/shared.py with your Cloud Namespace IDs and Endpoint names
```



---

## Architecture Overview

### Stage 2: Cross-Namespace Architecture with Temporal Nexus

```
┌────────────────────────────────────────────────────────────────┐
│                     Orchestrator Workflow                      │
│                    (default namespace)                         │
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
    │         │----------------------
    ▼                               ▼
┌──────────────────┐    ┌─────────────────────┐
│  IT Namespace    │    │  Finance Namespace  │
│                  │    │                     │
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
└──────────────────┘    └─────────────────────┘
```

### Key Architectural Decisions

#### ✅ Nexus Calls from Workflow (Not Activities)

This demo has two Nexus calls available: 
- `_discover_remote_tools()` - Calls Nexus to list available tools
- `_execute_nexus_tool()` - Calls Nexus to execute remote tools

`_discover_remote_tools` is called at the start of the main orchestrator worker, with the assumption that remote tools wont be added frequently, therefore this is a one time deterministic call made at the Temporal Workflow level. The Python SDK supports this.

However, `_execute_nexus_tool()` is meant to be called inside the while loop of the Orchestrator, based on the LLM determining this is the next step to be taken. In theory, this should be an activity, since tool calls are non-deterministic. However this is actually a deterministic call to the Nexus endpoint. It is eventually picked up by the respective Nexus handler, that calls the tool and returns the result.

The point to note is that in the current implementation, the Nexus handler is calling the tool as a regular function, so it wont have the Temporal retries and durability guarantees. For longer run or brittle functions, the Nexus handler should call a workflow in the remote location, which would then call the tool as an activity.

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

![Alt Text](images/app_flow_with_nexus.png)


## Note
This implementation is for educational purposes only and is not intended to be used in production. Current limitations include no context window management and no session management.