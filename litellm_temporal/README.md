# Durable Agent Loop - LiteLLM Implementation

**Approach:** Manual agent orchestration with LiteLLM for multi-provider LLM support

This implementation demonstrates a complete durable agent loop built with:
- **Manual agent orchestration** - Explicit while loop with full control over agent decisions
- **LiteLLM** - Support for any LLM provider (OpenAI, Anthropic Claude, Google Gemini, etc.)
- **Temporal activities** - Plan next action and execute tools as durable activities
- **Nexus operations** - Cross-namespace tool execution (IT and Finance services)
- **Manual conversation memory** - Explicit tracking of conversation history
- **Multi-turn conversations** - Interactive chat via Temporal Updates

## Architecture

### Components

1. **Orchestrator Workflow** (`app/workflow.py`)
   - Main agent loop (while True)
   - Manual conversation history tracking
   - Manual tool routing and execution
   - Nexus client creation and operation calls

2. **Activities** (`app/activities.py`)
   - `plan_next_action()` - LLM decides next step (uses LiteLLM)
   - `execute_tool()` - Execute local tools (calculator, echo)

3. **Nexus Services** (Remote namespaces)
   - IT Service: jira_metrics, get_ip
   - Finance Service: stock_price, calculate_roi

4. **Workers**
   - `orchestrator_worker.py` - Main workflow and activities
   - `it_nexus_worker.py` - IT tools in separate namespace
   - `finance_nexus_worker.py` - Finance tools in separate namespace

5. **Client** (`client.py`)
   - Interactive CLI for multi-turn conversations
   - Uses Temporal Updates for request/response

## Prerequisites

1. **Temporal Server** running locally:
   ```bash
   temporal server start-dev
   ```

2. **Python 3.11+** with uv:
   ```bash
   # Install uv if needed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **LLM API Key** (OpenAI, Anthropic, etc.):
   ```bash
   # For OpenAI
   export OPENAI_API_KEY=your_key_here

   # For Anthropic
   export ANTHROPIC_API_KEY=your_key_here
   ```

## Setup

1. **Navigate to this directory:**
   ```bash
   cd litellm_temporal
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

4. **Create Nexus endpoints** (one-time setup):
   ```bash
   # Create namespaces
   temporal operator namespace create --namespace it-namespace
   temporal operator namespace create --namespace finance-namespace

   # Create Nexus endpoints
   temporal operator nexus endpoint create \
     --name it-nexus-endpoint \
     --target-namespace it-namespace \
     --target-task-queue it-tools-queue

   temporal operator nexus endpoint create \
     --name finance-nexus-endpoint \
     --target-namespace finance-namespace \
     --target-task-queue finance-tools-queue
   ```

## Running the Demo

You need **3 terminal windows** running simultaneously:

### Terminal 1: IT Nexus Worker
```bash
cd litellm_temporal
uv run it_nexus_worker.py
```

### Terminal 2: Finance Nexus Worker
```bash
cd litellm_temporal
uv run finance_nexus_worker.py
```

### Terminal 3: Orchestrator Worker
```bash
cd litellm_temporal
uv run orchestrator_worker.py
```

### Terminal 4: Client (Interactive Chat)
```bash
cd litellm_temporal
uv run client.py
```

## Example Interactions

```
You: Calculate 15 * 23
Agent: The result is 345.

You: What is my IP address?
Agent: Your IP address is 172.16.0.1

You: What is the stock price of AAPL?
Agent: The current stock price of AAPL is $185.50

You: Calculate the ROI for $10000 invested at 5% for 10 years
Agent: The ROI for $10,000 invested at 5% annually over 10 years is $16,288.95

You: quit
```

## Switching LLM Providers

This implementation uses LiteLLM, so you can easily switch providers by:

1. **Edit `app/llm_client.py`** and change the model:
   ```python
   # For OpenAI (default)
   model="gpt-4"

   # For Anthropic Claude
   model="claude-3-5-sonnet-20241022"

   # For Google Gemini
   model="gemini/gemini-pro"
   ```

2. **Set appropriate API key:**
   ```bash
   # For Claude
   export ANTHROPIC_API_KEY=your_key

   # For Gemini
   export GOOGLE_API_KEY=your_key
   ```

3. **Restart workers** for changes to take effect

## Code Structure

```
litellm_temporal/
├── app/
│   ├── activities.py              # plan_next_action, execute_tool
│   ├── workflow.py                # Main agent loop
│   ├── llm_client.py              # LiteLLM client configuration
│   ├── it_activities.py           # IT tool implementations
│   ├── finance_activities.py      # Finance tool implementations
│   ├── it_service.py              # IT Nexus service definition
│   ├── finance_service.py         # Finance Nexus service definition
│   ├── it_nexus_handler.py        # IT Nexus handlers
│   ├── finance_nexus_handler.py   # Finance Nexus handlers
│   └── shared.py                  # Shared constants
├── orchestrator_worker.py         # Main workflow worker
├── client.py                      # Interactive CLI client
├── it_nexus_worker.py             # IT namespace worker
├── finance_nexus_worker.py        # Finance namespace worker
└── pyproject.toml                 # Dependencies
```

## Key Patterns

### Manual Agent Loop
```python
while True:
    # Manual conversation history tracking
    self.conversation_history.append({"role": "user", "content": message})

    # LLM decides next action
    plan = await workflow.execute_activity(
        AgentActivities.plan_next_action,
        args=[context, self.conversation_history, self.remote_tools],
    )

    # Manual tool routing
    if plan.next_step == "execute_tool":
        result = await workflow.execute_activity(
            AgentActivities.execute_tool,
            args=[plan.tool_name, plan.tool_args]
        )
```

### Manual Nexus Calls
```python
# Create Nexus client
client = workflow.create_nexus_client(service=ITService, endpoint="it-nexus-endpoint")

# Execute operation
result = await client.execute_operation(
    ITService.execute_tool,
    {"tool_name": "jira_metrics", "args": {...}}
)
```

### Multi-Turn with Updates
```python
@workflow.update
async def send_message(self, message: str) -> str:
    """Send message and wait for response"""
    self.current_message = message
    await workflow.wait_condition(lambda: self.pending_response is not None)
    response = self.pending_response
    self.pending_response = None
    return response
```

## Advantages

- ✅ **Full control** - See every step of agent decision-making
- ✅ **Educational** - Clear visibility into agent loop patterns
- ✅ **Multi-provider** - Use any LLM via LiteLLM
- ✅ **Flexible** - Easy to customize agent logic
- ✅ **Production-ready** - Stable Temporal patterns

## Disadvantages

- ❌ **More code** - ~200-300 lines in workflow
- ❌ **Manual management** - Must track history, route tools, etc.
- ❌ **Provider switching** - Requires code changes to switch LLMs

## Comparison

For a simpler alternative using OpenAI Agents SDK, see `../openai_temporal/`

| Feature | This (litellm_temporal) | openai_temporal |
|---------|-------------------------|-----------------|
| Code Size | ~200-300 lines | ~30-50 lines |
| Agent Loop | Manual while loop | SDK managed |
| LLM Support | Any (via LiteLLM) | Any (via LiteLLM) |
| Provider Switching | Code changes required | Config file change |
| Control Level | Full control | Convention over config |
| Educational Value | High | Medium |

## Troubleshooting

**Workers not connecting:**
- Ensure Temporal server is running: `temporal server start-dev`
- Check namespaces exist: `temporal operator namespace list`

**Nexus errors:**
- Verify Nexus endpoints: `temporal operator nexus endpoint list`
- Ensure IT and Finance workers are running

**LLM errors:**
- Check API key is set: `echo $OPENAI_API_KEY`
- Verify LiteLLM model format: https://docs.litellm.ai/docs/providers

**Import errors:**
- Make sure you're running from `litellm_temporal/` directory
- Run `uv sync` to ensure dependencies are installed

## Learn More

- [Temporal Documentation](https://docs.temporal.io)
- [Temporal Nexus](https://docs.temporal.io/nexus)
- [LiteLLM Providers](https://docs.litellm.ai/docs/providers)
- [Temporal Python SDK](https://github.com/temporalio/sdk-python)
