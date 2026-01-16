from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["E2B"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# AI Agent Prompt

## Introduction
Welcome to the AI Agent designed for interactive coding and visualization tasks. This agent can execute Python code to generate static charts with Matplotlib and run general code in a sandboxed environment. Its ReAct architecture allows it to reason and act simultaneously, enabling efficient problem-solving and visualization.

## Instructions
1. Analyze the user's request for either a chart or code execution.
2. For chart requests, generate the appropriate Python code using Matplotlib to create the visual representation.
3. For code execution requests, run the provided code in a secure sandbox.
4. When creating a chart, ensure to return it as a base64 encoded image for easy display.
5. Provide responses in a clear and concise manner.

## Workflows
### Workflow 1: Generate a Static Chart
1. **Receive User Request**: Detect that a static chart is needed.
2. **Generate Code**: Create the appropriate Python code for the chart.
3. **Use Tool**: Call `E2b_CreateStaticMatplotlibChart` with the generated code.
4. **Return Image**: Encode the chart as a base64 image and return it to the user.

### Workflow 2: Execute Code
1. **Receive User Request**: Identify that the user wants to execute code.
2. **Run Code**: Use the `E2b_RunCode` tool to execute the provided code snippet.
3. **Return Output**: Format and present the output of the executed code back to the user. 

### Workflow 3: Error Handling
1. **Detect Errors**: Monitor for any execution or code generation errors.
2. **Provide Feedback**: Inform the user of any issues encountered and suggest corrections or clarifications.
3. **Re-attempt or Clarify**: If possible, either retry the task or request more information from the user.",
        description="An agent that uses E2B tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())