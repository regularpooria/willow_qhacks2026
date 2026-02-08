import json
from openai import OpenAI
from public.tools.tools import execute_tool, get_tool_specs
from dotenv import load_dotenv
import os
import sys


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Load .env from the correct location
load_dotenv(resource_path(".env"))

messages = []


def LLM_call(transcript):
    tools = get_tool_specs()
    print(tools)

    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
    messages.append({"role": "user", "content": transcript})

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
    )

    messages.append(response.choices[0].message)

    # Loop until no more tool calls are needed
    max_iterations = 10
    iteration = 0

    while response.choices[0].message.tool_calls and iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Tool execution iteration {iteration}")

        for tool_call in response.choices[0].message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            print(f"🔧 Executing: {tool_call.function.name}")
            print(f"   Args: {args}")
            execute_tool(tool_call.function.name, args)

            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": "success"}
            )

        # Get next response (might have more tool calls or final answer)
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools=tools,
        )

        messages.append(response.choices[0].message)

    # Return final response text
    final_response = response.choices[0].message.content
    print(f"✅ Final response: {final_response}")
    return final_response


if __name__ == "__main__":
    LLM_call("open browser")
    LLM_call("search youtube for cat videos")
