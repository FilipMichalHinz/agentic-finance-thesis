import json
from typing import List

from langchain_core.messages import ToolMessage


def _coerce_args(args):
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"input": args}
    if isinstance(args, dict):
        return args
    return {"input": args}


def run_with_tools(llm, messages, tools, max_iterations: int = 3):
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}

    for _ in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        if not getattr(response, "tool_calls", None):
            return response

        messages.append(response)
        for call in response.tool_calls:
            tool = tool_map.get(call["name"])
            if not tool:
                messages.append(
                    ToolMessage(
                        content=f"Unknown tool: {call['name']}",
                        tool_call_id=call["id"],
                    )
                )
                continue
            args = _coerce_args(call.get("args"))
            result = tool.invoke(args)
            messages.append(
                ToolMessage(
                    content=json.dumps(result, ensure_ascii=True),
                    tool_call_id=call["id"],
                )
            )

    return response
