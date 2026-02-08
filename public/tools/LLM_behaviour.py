import json
from openai import OpenAI
from public.tools.tools import execute_tool, get_tool_specs
from dotenv import load_dotenv


load_dotenv()


import os


def LLM_call(transcript):

    tools = get_tool_specs()
    # print(tools)

    # call LLM

    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
    system_prompt = "You are a general browser control assistant. You can interact with tools for YouTube, Google Maps, and general websites & search. After executing tools, respond with a single brief sentence (max 16 words) summarizing the result. Be concise and friendly."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript}
    ]

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
    )

    messages.append(response.choices[0].message)

    for tool_call in response.choices[0].message.tool_calls or []:
        args = json.loads(tool_call.function.arguments)
        print("\n\n " + str(tool_call))
        ret_val = execute_tool(tool_call.function.name, args)
        print("tool return: ", ret_val)

        # 4. Provide function call results to the model
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": "success"}
        )

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
    )

    # 5. The model should be able to give a response!
    print(response.choices[0].message.content)
    return response.choices[0].message.content
    # calls tool

    # returns current state

    # returns response transcripts

    # transcript to audio

    # return state, response
    pass


if __name__ == "__main__":

    LLM_call("open browser")
    LLM_call("search youtube for cat videos")
