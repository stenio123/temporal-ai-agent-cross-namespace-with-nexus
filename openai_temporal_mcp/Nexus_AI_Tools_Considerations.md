# Nexus + AI Tools Integration: Architecture Considerations

## Overview

When integrating Temporal Nexus with OpenAI Agents SDK, there are three primary approaches for exposing remote tools across namespaces. Each has different trade-offs between flexibility, complexity, and idiomatic usage.

---

## Approach 1: Static Operations (Individual Endpoints)

### Description
Each tool is defined as a separate Nexus operation. The orchestrator explicitly lists every remote tool.

```
IT Namespace exposes:
  - jira_metrics operation
  - get_ip operation

Finance Namespace exposes:
  - stock_price operation
  - calculate_roi operation

Orchestrator imports these and converts each to an agent tool.
```

### Benefits
- ✅ **Idiomatic Temporal Nexus**: Follows documented best practices
- ✅ **Type safety**: Each operation has explicit input/output types
- ✅ **No schema workarounds**: Works naturally with OpenAI strict schemas
- ✅ **Clear ownership**: Each operation is independently versioned

### Drawbacks
- ❌ **Tight coupling**: Orchestrator must update imports when new tools are added
- ❌ **Cross-team coordination required**: IT/Finance teams can't add tools independently
- ❌ **Less dynamic**: All tools must be known at orchestrator deployment time

### Best For
- Organizations with centralized control over tools
- Scenarios where tool stability is more important than flexibility
- When type safety and compile-time checks are critical

---

## Approach 2: Dispatcher Pattern (Generic Execute)

### Description
Each namespace exposes two operations: `list_tools` (for discovery) and `execute_tool` (generic dispatcher). The orchestrator discovers available tools at runtime and routes execution through the dispatcher.

```
IT Namespace exposes:
  - list_tools: Returns metadata about all available tools
  - execute_tool: Generic dispatcher that routes to specific tools

Orchestrator discovers tools dynamically and builds agent instructions at startup.
```

### Benefits
- ✅ **Cross-team flexibility**: IT/Finance teams can add tools without orchestrator changes
- ✅ **Runtime discovery**: Tools are discovered when the workflow starts
- ✅ **Operational independence**: Different teams manage their own tool namespaces
- ✅ **MCP-like patterns**: Similar to Model Context Protocol discovery

### Drawbacks
- ❌ **Generic types**: Uses flexible schemas (Pydantic workarounds needed)
- ❌ **Less idiomatic**: Fights against Temporal's static contract model
- ❌ **Additional complexity**: Discovery + dynamic instruction building required
- ❌ **Agent sees generic tool**: Agent calls "execute_tool" not natural tool names
- ❌ **OpenAI SDK incompatibility**: See Technical Blocker below

### Technical Blocker with `nexus_operation_as_tool()`

**Issue:** When using `nexus_operation_as_tool()` with dispatcher pattern, OpenAI's strict schema validation rejects flexible argument types:

- Using `Any` type → OpenAI error: "schema must have a 'type' key"
- Using `Dict[str, Any]` → OpenAI error: "additionalProperties should not be set for object types"
- Setting `strict_json_schema=False` → Still fails (schema validation happens before this flag is checked)

**Root Cause:** The dispatcher pattern requires flexible schemas to handle arbitrary tool arguments, but `nexus_operation_as_tool()` generates schemas that OpenAI's validation rejects even in non-strict mode.

**Workaround Status:** No viable workaround found. The integration between `nexus_operation_as_tool()` and OpenAI's schema requirements is incompatible with generic dispatcher operations.

### Best For
- ⚠️ **Not recommended with `nexus_operation_as_tool()`** due to schema compatibility issues
- May work if calling Nexus operations manually (not via `nexus_operation_as_tool()`)

---

## Approach 3: MCP (Model Context Protocol) Integration

### Description
Use Temporal's MCP server primitives instead of Nexus operations. MCP is specifically designed for dynamic tool discovery in AI agent contexts.

```
IT Namespace runs an MCP server
Finance Namespace runs an MCP server

Orchestrator connects to MCP servers via:
  - stateless_mcp_server()
  - stateful_mcp_server()

Agent discovers and calls tools via MCP protocol.
```

### Benefits
- ✅ **Purpose-built for AI agents**: MCP designed for dynamic tool discovery
- ✅ **Industry standard**: Protocol adopted across AI ecosystem
- ✅ **Native discovery**: Built-in support for tool listing and metadata
- ✅ **True runtime flexibility**: Tools can be added/removed without any redeployment

### Drawbacks
- ❌ **Different primitive**: Not using Nexus cross-namespace capabilities
- ❌ **Experimental in Temporal**: MCP integration still evolving
- ❌ **Learning curve**: New protocol and patterns to adopt
- ❌ **Less Temporal-native**: Loses some Temporal orchestration benefits

### Best For
- Future-looking architectures aligned with AI ecosystem trends
- Organizations prioritizing maximum flexibility
- Scenarios where tools need to be truly dynamic

---

## Current Implementation

**We chose Approach 1 (Static Operations)** after attempting Approach 2.

**Why we switched:**
1. Approach 2 hit a hard blocker with `nexus_operation_as_tool()` (see Technical Blocker above)
2. OpenAI's schema validation requirements are incompatible with dispatcher pattern
3. Approach 1 works immediately without schema workarounds
4. Trade-off accepted: Orchestrator must be updated when new tools are added

**What was attempted with Approach 2:**
- Initially implemented dispatcher pattern for cross-team flexibility
- Encountered OpenAI schema validation errors (both `Any` and `Dict[str, Any]` types rejected)
- Tried `strict_json_schema=False` parameter (did not resolve issue)
- Attempted Pydantic model configurations (no viable solution found)

---

## Recommendation for Future

Consider **evaluating Approach 3 (MCP)** when:
- Temporal's MCP integration reaches stable release
- Tool discovery becomes more complex (many namespaces, frequent changes)
- Standardization with broader AI tooling ecosystem is desired
- Dynamic tool discovery is required (Approach 2 is currently blocked)

---

## Summary Table

| Aspect | Static Operations | Dispatcher Pattern | MCP Integration |
|--------|------------------|-------------------|-----------------|
| **Cross-team independence** | ❌ No | ✅ Yes | ✅ Yes |
| **Type safety** | ✅ Strong | ⚠️ Flexible | ⚠️ Protocol-based |
| **Idiomatic Temporal** | ✅ Yes | ⚠️ Workarounds | ❌ Different primitive |
| **Complexity** | ✅ Low | ⚠️ Medium | ❌ High |
| **Runtime flexibility** | ❌ Static | ✅ Dynamic discovery | ✅ Fully dynamic |
| **`nexus_operation_as_tool()` compatible** | ✅ Yes | ❌ **Schema blocker** | N/A |
| **Production readiness** | ✅ Stable | ❌ Blocked | ⚠️ Experimental |

---

## Feedback for Temporal Team

### Issue Summary
The dispatcher pattern (generic `execute_tool` operation) is incompatible with `nexus_operation_as_tool()` due to OpenAI schema validation requirements.

### Reproduction
1. Define Nexus operation with flexible types: `execute_tool: nexusrpc.Operation[ToolExecutionInput, ToolExecutionResult]` where `ToolExecutionInput` contains `args: Any` or `args: Dict[str, Any]`
2. Convert to tool: `nexus_operation_as_tool(Service.execute_tool, service=Service, endpoint="...", strict_json_schema=False)`
3. Start workflow → OpenAI schema validation error

### Expected vs Actual
- **Expected:** `strict_json_schema=False` would allow flexible schemas
- **Actual:** Schema validation fails regardless of `strict_json_schema` setting

### Impact
- Blocks dispatcher pattern for cross-namespace tool routing
- Forces static tool definitions (orchestrator must know all tools at deploy time)
- Reduces flexibility for multi-team tool development

### Suggested Solutions
1. Allow `strict_json_schema=False` to truly bypass schema validation
2. Provide guidance on dispatcher patterns with OpenAI Agents SDK
3. Document that MCP is the recommended approach for dynamic tool discovery

### Workaround
Use individual Nexus operations per tool (Approach 1 in this document).
