Community discussion:

Hi. We are trying to use temporal with openai agent sdk. We need to be able to set the headers of our mcp server in the workflow. Is this possible? (edited) 
16 repliesTim Conley  [11:51 AM]
Can you give me a bit more context? Are you trying to use mcp_servers or the HostedMCPTool? I assume the former, but I want to be sure.

Assuming that's the case, you are able to set the headers globally when you construct the server in the worker with
lambda: MCPServerStreamableHttp(
    name="StreamableHttpServer",
    params={
        "url": "http://localhost:8000/mcp",
        "headers": {"header": "value"}
    },
)We don't currently have an easy way to provide a separate configuration for different workflows, which might be what you are asking for. You would have to define multiple servers by name if that is possible (the headers aren't dynamically generated in the workflow). If this doesn't work for you, we can open a feature request.
Morgan Cromell  [12:27 PM]
I'm trying to use mcp_server. Our server uses the header to run the tools on behalf of that user. So we need to be able to control the headers on a per workflow run basis
[12:28 PM]Would be awesome if the factory for the mcp server could take arguments
Tim Conley  [12:29 PM]
Are you trying to use Stateful or Stateless? Just so I can speak to the specifics.
Morgan Cromell  [12:30 PM]
Stateless
Tim Conley  [12:31 PM]
It's a little more complicated than just adding arguments to the factory because the factory is actually invoked inside an activity, not in the workflow context where your headers, etc. would exist. So we would need to ensure that the set of options, (headers, etc.) would be serializable and stored as part of the activity input. And think about backwards compatibility (or just make a breaking change)
Morgan Cromell  [12:34 PM]
Yeah dived into the source code a bit and saw that. Might just tinker around and implement my own wrapper based on it
Tim Conley  [12:36 PM]
I was thinking about whether you would be able to implement it on your own, which might be easier given the more strict assumptions you are able to make for your particular use case. The one problem you'll run into is:
                if not isinstance(
                    s,
                    (
                        _StatelessMCPServerReference,
                        _StatefulMCPServerReference,
                    ),
                ):
                    raise ValueError(
                        f"Unknown mcp_server type {type(s)} may not work durably."
                    )We currently disallow any other server implementation because they are likely to break in confusing sandbox ways.
[12:37 PM]I think we'd potentially be open to loosening that restriction if you do want to proceed that way. It was put in place on a principle of "we can always loosen but not tighten"
Tim Conley  [1:12 PM]
I've created a feature request for the scenario:
https://github.com/temporalio/sdk-python/issues/1146
Morgan Cromell  [1:39 PM]
Implemented my own MCPServerProvider on top of the existing one. And with some additional type wrangling I got arguments working. I'm just sending a dict as an addition argument to all the mcp activities that I send to the factory.
Tim Conley  [1:42 PM]
Where is the dict coming from? Unless I'm misunderstanding, you would have to pass it across the activity, which would involve changing the _StatelessMCPServerReference as well. Or are the arguments you want to pass available when you instantiate your new server provider?
Morgan Cromell  [1:47 PM]
Yes i had to make another version of _StatelessMCPServerReference aswell.
Tim Conley  [1:47 PM]
Gotcha. We'll keep the issue to make this easier for others, and make it so you don't need to reference a private object.
Morgan Cromell  [1:52 PM]
Yeah. Official support would of course be preferred. Just glad i did not get stuck on this 
But i think it would need to be a breaking change as it changes the activity argument count. Maybe those should be changed to a single argument that can just be expanded in the future to avoid breaking changes.Tim Conley  [1:53 PM]
A breaking change to the definition of the factory callable as well since it would take an argument. All the OpenAI integration is still in preview, so it is possible, but yes.

-----
Internal discussion:

At quick glance, if there is metadata one wants to provide as part of MCP server invocation, we should allow it and plumb it through the activity input
[12:40 PM]Ideally our internal activity input dataclass can have additional optional fields added compatibly (edited) 
Tim Conley  [12:41 PM]
I'm a bit concerned around the typing and such for it, because depending on the server the start arguments are different.
Chad Retz  [12:41 PM]
I admit I don't know the details of these two servers and what data types they accept for headers
Tim Conley  [12:41 PM]
We'd have to essentially take a dict[str, Any] and cast it into the appropriate TypedDict for the servers
[12:42 PM]This isn't Stateless vs Stateful it's stdio vs streamablehttp vs sse
Chad Retz  [12:42 PM]
And what data types do each accept as headers?
Tim Conley  [12:42 PM]
Headers for instance, aren't relevant for stdio
[12:42 PM]Just aren't a thing
[12:43 PM]class MCPServerStdioParams(TypedDict):
class MCPServerStreamableHttpParams(TypedDict):
[12:43 PM]et cetera
[12:44 PM]The alternative would be to allow the user to define their own MCPServer which does this in a similar way but with their assumptions in place. "I'm going to be calling StreamableHTTP, so put these headers in the activity"
Chad Retz  [12:44 PM]
I only see headers in MCPServerStreamableHttpParams not in MCPServerStdioParams
Tim Conley  [12:45 PM]
Yes.
Headers for instance, aren't relevant for stdioChad Retz  [12:47 PM]
Sorry, refamiliarizing myself with how users use MCP from inside a workflow...
Tim Conley  [12:48 PM]
Inside, they refer to some registered server by name, but don't really know what type of MCPServer it is
[12:48 PM]At least not type-wise
Chad Retz  [12:48 PM]
Before I give a recommendation, I need to understand the use case of setting these options from a workflow or not. I am struggling to understand whether these headers are initialization time headers or situational
[12:49 PM]For instance, can I have two instances of the same MCP named server with different headers defined by some workflow input?
Tim Conley  [12:49 PM]
According to the user, they want to set headers about the "user they are running the workflow for" in essence. So it would be dynamic from workflow input
[12:50 PM]That's what I asked as well, it really isn't a set of static servers
Chad Retz  [12:50 PM]
Can you help me understand again when we instantiate the MCP servers on a user's behalf? Is it per agent? Meaning two agents may have different instances of the same MCP servers correct?
Tim Conley  [12:51 PM]
Depends on the user's code and stateless vs stateful. User is using stateless, we instantiate the server for every call
[12:51 PM]In stateful, it is when they do async with server:
Chad Retz  [12:52 PM]
Ah, I see openai_agents.workflow.stateless_mcp_server and openai_agents.workflow.stateful_mcp_server now. Sec, trying to understand the relationship of one params type to another before giving final recommendation, heh
[12:55 PM]Ok, I think I have an idea. I think the openai_agents.workflow.stateless_mcp_server and openai_agents.workflow.stateful_mcp_server should accept a additional_data: Any, and then StatelessMCPServerProvider and StatefulMCPServerProvider should pass that additional_data as the parameter to the callable that instantiates the MCP server (edited) 
[12:56 PM]If a user wants to have a contract with themselves on how that additional data translates into the server instantiation, they can
Tim Conley  [12:56 PM]
That's definitely the option if we handle it, I agree. Don't love the "This can be any, better serialize" but it should work
Chad Retz  [12:57 PM]
The other option would be to be more type-safe in your server references instead of using strings. We absolutely should leverage the type hint of the server-creation callable if it's present (which I understand is not the case for lambda). Alternatively, we can accept an additional_data_type_hint in the State(less|ful)MCPServerProvider constructor (edited) 
Tim Conley  [12:59 PM]
The other option would be to be more type-safe in your server references instead of using stringsI don't think this is possible while still being generic to MCPServer which was a goal
Chad Retz  [1:01 PM]
It'd be something like type MCPServerRef[T] = NewType('MCPServerRef') or something, I haven't sat and thought
[1:02 PM]You only need a type-safe reference, which at this time is just string name and additional data type. But this seems niche enough to not need it (edited) 
Tim Conley  [1:02 PM]
But it needs to match against the callable which doesn't exist there in order to actually validate anything I think
[1:02 PM]That said, I agree it's more a nice to have than required to make this work
Chad Retz  [1:02 PM]
Yeah, I suspect you'd accept the ref when instantiating the provider to ensure it is valid
Tim Conley  [1:03 PM]
I think that would still be more or less a pinky promise, because the refs wouldn't necessarily be the same when actually used in the workflow
Chad Retz  [1:04 PM]
I agree, string name is acceptable pinky promise, but sans type safety, same promise has to be made by both sides of the "additional constructor data" usage (edited) 
Tim Conley  [1:55 PM]
Currently the mcp activities take multiple arguments, so adding another would break replay. Should we take the opportunity to change them all to objects? There will be quite a few since the stateful/stateless would now have a different set of arguments
[1:55 PM]It is what we recommend after all
Chad Retz  [1:58 PM]
Currently the mcp activities take multiple arguments, so adding another would break replayLooks like we didn't follow our own best practice here: https://docs.temporal.io/develop/python/core-application#activity-parameters. I am not sure adding another optional parameter does break replay, would have to test. But in general we should follow our own best practice here of single dataclass for all parameters.
Tim Conley  [1:59 PM]
I'll check for replay breaking. I thought it did, but that may actually be because of changes I made to the test workflow instead.

In this case it wouldn't have really helped because some methods went from 0 arguments to an argument
Chad Retz  [2:01 PM]
It wouldn't necessarily be replay it'd break anyways (we don't check activity arguments during replay), but rather newer-code activity invocation from older-code workflow (too few parameters passed), but I would guess we work with optional additional params, will take a peek in activity worker (edited) 
Tim Conley  [2:02 PM]
Seems like it does not break replay when I make the minimal workflow changes
Chad Retz  [2:04 PM]
Yeah, so we literally use type hints if they are there to convert args, but always pass the literal number of args given to the function given. So an optional arg should be fine. Having said that, there would be an issue during rollout where new-code workflow started old-code activity (too many parameters). If we are concerned about compatibility, we need to do this across multiple releases I think (first release accept extra param but don't send it, second release start sending it).
Tim Conley  [2:05 PM]
"cause": {
      "message": "StatelessMCPServerProvider._get_activities.<locals>.list_tools() missing 1 required positional argument: 'factory_argument'",
      "stackTrace": "  File \"/Users/tconley/sdk-python/temporalio/worker/_activity.py\", line 319, in _handle_start_activity_task
    result = await self._execute_activity(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        start, running_activity, task_token, data_converter
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )Chad Retz  [2:05 PM]
Required positional argument? (edited) 
Tim Conley  [2:05 PM]
Doesn't seem like it works calling with too few args
[2:06 PM]I changed it so that the current code is activity has an optional argument, execute doesn't provide any. This happened
Chad Retz  [2:06 PM]
Can I see factory_argument in the func signature? (edited) 
Tim Conley  [2:06 PM]
async def list_tools(factory_argument: Optional[Any]) -> list[MCPTool]:Chad Retz  [2:06 PM]
Ah, that is required, try factory_argument: Optional[Any] = None
Tim Conley  [2:06 PM]
Oh I was confusing "optional" with option param
[2:07 PM]I've been doing typescript now
Chad Retz  [2:07 PM]
However, would recommend async def list_tools(request: Optional[ListToolsRequest] = None) -> list[MCPTool]: though I understand with some others this can't be done
Tim Conley  [2:08 PM]
Not without a compat break, and it would need to be Optional[StatelessListToolsRequest] because they differ
Chad Retz  [2:08 PM]
Though for this use case, I would have expected connect to get the parameter
Tim Conley  [2:08 PM]
For stateful, yes
Chad Retz  [2:08 PM]
Ah, makes sense. And now that I think about it, not sure you have the new-code workflow with +1 param to old-code activity issue either because I think we're supposed to be lopping off extra args for just this issue, let me see if that's true
Tim Conley  [2:09 PM]
Do you think it is worth bringing everything in line with single arguments? It would break replay, but it might be a good idea to do now if we strongly recommend it
Chad Retz  [2:09 PM]
Well no, maybe not
Tim Conley  [2:10 PM]
This will already be a breaking change, though not a replay breaking change
Chad Retz  [2:10 PM]
Note, none of this breaks replay since that does not check activity arguments, it only affects when the activity invocation is attempted if the params aren't what the code can accept
Tim Conley  [2:11 PM]
Okay yes, good to differentiate
Chad Retz  [2:12 PM]
I do think it'd be wise to have single dataclass params for everything, but I am not sure I am confident enough to make a decision on whether breaking users that way is best. Note, the way these breaks usually manifest is during rollout (caller side has a different version of the library than activity worker side), and we do have built-in retry
[2:13 PM]And I don't think we're removing trailing activity parameters if there are more than the function can accept, but I think other SDKs might be, that might be worth investigating (edited) 
Tim Conley  [2:14 PM]
On the one hand, the whole thing only went in three weeks ago. On the other, I'm not sure how much practical impact there is
[2:14 PM]{
  "message": "StatelessMCPServerProvider._get_activities.<locals>.list_tools() takes 0 positional arguments but 1 was given",
  "applicationFailureInfo": {
    "type": "TypeError"
  }
}Chad Retz  [2:14 PM]
We reserve the right pre-GA to do any changes, so it's just up to us on impact vs value. I think the impact will be rather low (it'll only occur for people who have started activities with a different code version than they are running activities on).
[2:15 PM]Right, that will happen if you have new-code workflow calling old-code activity, that's the primary break here (edited) 
Tim Conley  [2:15 PM]
Makes sense
[2:15 PM]Signed up for standup consideration