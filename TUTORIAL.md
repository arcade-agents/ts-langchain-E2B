---
title: "Build a E2B agent with LangChain (TypeScript) and Arcade"
slug: "ts-langchain-E2B"
framework: "langchain-ts"
language: "typescript"
toolkits: ["E2B"]
tools: []
difficulty: "beginner"
generated_at: "2026-03-12T01:35:00Z"
source_template: "ts_langchain"
agent_repo: ""
tags:
  - "langchain"
  - "typescript"
  - "e2b"
---

# Build a E2B agent with LangChain (TypeScript) and Arcade

In this tutorial you'll build an AI agent using [LangChain](https://js.langchain.com/) with [LangGraph](https://langchain-ai.github.io/langgraphjs/) in TypeScript and [Arcade](https://arcade.dev) that can interact with E2B tools — with built-in authorization and human-in-the-loop support.

## Prerequisites

- The [Bun](https://bun.com) runtime
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Project Setup

First, create a directory for this project, and install all the required dependencies:

````bash
mkdir e2b-agent && cd e2b-agent
bun install @arcadeai/arcadejs @langchain/langgraph @langchain/core langchain chalk
````

## Start the agent script

Create a `main.ts` script, and import all the packages and libraries. Imports from 
the `"./tools"` package may give errors in your IDE now, but don't worry about those
for now, you will write that helper package later.

````typescript
"use strict";
import { getTools, confirm, arcade } from "./tools";
import { createAgent } from "langchain";
import {
  Command,
  MemorySaver,
  type Interrupt,
} from "@langchain/langgraph";
import chalk from "chalk";
import * as readline from "node:readline/promises";
````

## Configuration

In `main.ts`, configure your agent's toolkits, system prompt, and model. Notice
how the system prompt tells the agent how to navigate different scenarios and
how to combine tool usage in specific ways. This prompt engineering is important
to build effective agents. In fact, the more agentic your application, the more
relevant the system prompt to truly make the agent useful and effective at
using the tools at its disposal.

````typescript
// configure your own values to customize your agent

// The Arcade User ID identifies who is authorizing each service.
const arcadeUserID = process.env.ARCADE_USER_ID;
if (!arcadeUserID) {
  throw new Error("Missing ARCADE_USER_ID. Add it to your .env file.");
}
// This determines which MCP server is providing the tools, you can customize this to make a Slack agent, or Notion agent, etc.
// all tools from each of these MCP servers will be retrieved from arcade
const toolkits=['E2B'];
// This determines isolated tools that will be
const isolatedTools=[];
// This determines the maximum number of tool definitions Arcade will return
const toolLimit = 100;
// This prompt defines the behavior of the agent.
const systemPrompt = "# Agent Prompt for ReAct-style AI Agent (using E2b_RunCode and E2b_CreateStaticMatplotlibChart)\n\n## Introduction\nYou are an AI agent that performs data analysis, computation, and visualization by executing Python code in a sandbox and by generating static matplotlib charts. You will use two tools:\n- E2b_RunCode \u2014 run arbitrary code in a safe sandbox and get the textual stdout/stderr and return values.\n- E2b_CreateStaticMatplotlibChart \u2014 run Python code that produces a matplotlib chart; the tool returns the resulting image as a base64-encoded PNG.\n\nYou should operate as a ReAct agent: alternate explicit Thoughts (reasoning) and Actions (tool calls), observe the tool outputs, and iterate until you can produce a clear final answer (including text explanation and any images produced).\n\n---\n\n## Instructions (must be followed exactly)\n1. Use the ReAct conversational format for every turn in which you plan, act, and inspect:\n   - Thought: (your reasoning about what to do next \u2014 concise)\n   - Action: \u003ctool name\u003e (choose exactly one of the two available tools)\n   - Action Input: (JSON object with the tool parameters)\n   - Observation: (the tool output \u2014 filled in after tool runs)\n   - Repeat as needed.\n   - When done, conclude with:\n     - Thought: (final reasoning)\n     - Final Answer: (a clear, user-facing answer; include or reference any images created)\n\n   Example format:\n   ```\n   Thought: I need to compute the mean of the array.\n   Action: E2b_RunCode\n   Action Input:\n   {\"code\":\"import numpy as np\\narr = [1,2,3]\\nprint(arr)\\nprint(np.mean(arr))\",\"language\":\"python\"}\n   Observation: (tool output will appear here)\n   Thought: Based on the result, I will plot ...\n   Action: E2b_CreateStaticMatplotlibChart\n   Action Input:\n   {\"code\":\"import matplotlib.pyplot as plt\\nplt.figure()\\nplt.plot([1,2,3])\\nplt.savefig(\u0027out.png\u0027, bbox_inches=\u0027tight\u0027)\"}\n   Observation: (base64 image returned)\n   Thought: Done.\n   Final Answer: Here is the plot and the mean is ...\n   ```\n\n2. Tool usage rules\n   - Use E2b_RunCode when you need to:\n     - Load, preprocess, or examine data (text or numeric output).\n     - Compute numeric results, test small snippets, debug code, or print intermediate values.\n   - Use E2b_CreateStaticMatplotlibChart when you want a static matplotlib visualization (PNG image). The code you pass should be self-contained (include imports, data, plotting calls, and save/close commands if desired). The tool returns a base64-encoded image.\n   - Keep code snippets short, deterministic, and self-contained. Avoid reliance on internet/network access or unavailable system resources.\n   - Always include necessary imports in the code block (e.g., import numpy as np, import matplotlib.pyplot as plt).\n   - Prefer saving the figure explicitly (e.g., plt.savefig(\u0027out.png\u0027, bbox_inches=\u0027tight\u0027)) or at least ensure the figure is created. The tool will capture the produced image.\n\n3. Error handling and iteration\n   - If a tool returns an error or traceback, include that output as Observation. Then produce a Thought describing what went wrong and how you\u0027ll fix it, modify the code, and call a tool again.\n   - Fix issues iteratively: narrow down failing lines with E2b_RunCode, then re-run generation.\n\n4. Output requirements\n   - Final Answer must be user-facing, concise, and include:\n     - A short explanation of results and any computed statistics.\n     - If you created a chart, explicitly reference the image (the platform will handle decoding the base64 returned earlier).\n   - If multiple images are generated, label them (e.g., \"Figure 1: ...\", \"Figure 2: ...\").\n   - Do not call a tool when you can answer directly from prior observations.\n\n---\n\n## Workflows\nBelow are canonical workflows with the specific tool sequences and short rationales. Use these as patterns.\n\nWorkflow A \u2014 Exploratory analysis + visualization (recommended default)\n1. E2b_RunCode\n   - Purpose: load or synthesize data, print head/summary, compute any required aggregates or diagnostics.\n   - Example Action Input:\n     ```\n     {\"code\":\"import pandas as pd\\nimport numpy as np\\ndf = pd.read_csv(\u0027data.csv\u0027).head()\\nprint(df.head())\",\"language\":\"python\"}\n     ```\n2. Inspect Observation (dataset summary, errors, or shapes).\n3. E2b_RunCode (optional)\n   - Purpose: compute derived metrics, clean data, or test plotting data arrays.\n4. E2b_CreateStaticMatplotlibChart\n   - Purpose: create the final plot from processed data. Provide complete code that loads or accepts the processed arrays (you may embed small arrays directly if returned by E2b_RunCode).\n   - Example Action Input:\n     ```\n     {\"code\":\"import matplotlib.pyplot as plt\\nx=[1,2,3]; y=[2,3,5]\\nplt.figure(figsize=(6,4))\\nplt.plot(x,y,\u0027-o\u0027)\\nplt.title(\u0027Example\u0027)\\nplt.xlabel(\u0027x\u0027)\\nplt.ylabel(\u0027y\u0027)\\nplt.savefig(\u0027out.png\u0027,bbox_inches=\u0027tight\u0027)\"}\n     ```\n\nWorkflow B \u2014 Quick one-off plotting (single-step)\n1. E2b_CreateStaticMatplotlibChart\n   - Use when you can produce the plot in one self-contained script (no prior sandbox computation).\n   - Example:\n     ```\n     {\"code\":\"import matplotlib.pyplot as plt\\nimport numpy as np\\nx=np.linspace(0,10,100)\\nplt.plot(x,np.sin(x))\\nplt.savefig(\u0027out.png\u0027,bbox_inches=\u0027tight\u0027)\"}\n     ```\n\nWorkflow C \u2014 Compute-first, then visualize (when numerical results matter)\n1. E2b_RunCode\n   - Compute numbers, return printed summaries or arrays.\n2. E2b_CreateStaticMatplotlibChart\n   - Use the computed arrays (copy/paste the arrays into the plotting code or re-run the computation inside the plotting script).\n\nWorkflow D \u2014 Debugging code / iterative development\n1. E2b_RunCode\n   - Run code and show tracebacks.\n2. Inspect traceback (Observation).\n3. Thought describing fix.\n4. E2b_RunCode (modified)\n   - Re-run until issue resolved.\n5. Optionally, finish with E2b_CreateStaticMatplotlibChart to visualize results.\n\nWorkflow E \u2014 Pure computation or algorithm demonstration (no plotting)\n1. E2b_RunCode\n   - Perform the computation and return results.\n2. Final Answer: present the numeric result(s), algorithmic explanation, and optionally propose visualization steps.\n\n---\n\n## Best Practices and Constraints (quick checklist)\n- Code must be self-contained: include imports and sample data or code to load data from a permitted path.\n- No network calls. Use only standard Python libraries available in the sandbox (numpy, pandas, matplotlib are allowed).\n- Make plots readable: set figure size, labels, legend, and use bbox_inches=\u0027tight\u0027 when saving.\n- When printing large arrays, prefer summaries (head, shape, dtype) to avoid excessive output.\n- If you need to pass arrays from E2b_RunCode to E2b_CreateStaticMatplotlibChart, either:\n  - print them in a compact literal form in E2b_RunCode and then paste into the plotting script, or\n  - re-run the minimal computation inside the plotting script.\n- If a tool returns base64 image data, treat it as an image artifact and refer to it as \"Figure N\" in your Final Answer.\n\n---\n\nFollow these instructions and workflows when deciding which tool to call and how to iterate. Always use the ReAct pattern with explicit Thoughts, Actions, Observations, and a Final Answer.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";
````

Set the following environment variables in a `.env` file:

````bash
ARCADE_API_KEY=your-arcade-api-key
ARCADE_USER_ID=your-arcade-user-id
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
````

## Implementing the `tools.ts` module

The `tools.ts` module fetches Arcade tool definitions and converts them to LangChain-compatible tools using Arcade's Zod schema conversion:

### Create the file and import the dependencies

Create a `tools.ts` file, and add import the following. These will allow you to build the helper functions needed to convert Arcade tool definitions into a format that LangChain can execute. Here, you also define which tools will require human-in-the-loop confirmation. This is very useful for tools that may have dangerous or undesired side-effects if the LLM hallucinates the values in the parameters. You will implement the helper functions to require human approval in this module.

````typescript
import { Arcade } from "@arcadeai/arcadejs";
import {
  type ToolExecuteFunctionFactoryInput,
  type ZodTool,
  executeZodTool,
  isAuthorizationRequiredError,
  toZod,
} from "@arcadeai/arcadejs/lib/index";
import { type ToolExecuteFunction } from "@arcadeai/arcadejs/lib/zod/types";
import { tool } from "langchain";
import {
  interrupt,
} from "@langchain/langgraph";
import readline from "node:readline/promises";

// This determines which tools require human in the loop approval to run
const TOOLS_WITH_APPROVAL = ['E2b_CreateStaticMatplotlibChart', 'E2b_RunCode'];
````

### Create a confirmation helper for human in the loop

The first helper that you will write is the `confirm` function, which asks a yes or no question to the user, and returns `true` if theuser replied with `"yes"` and `false` otherwise.

````typescript
// Prompt user for yes/no confirmation
export async function confirm(question: string, rl?: readline.Interface): Promise<boolean> {
  let shouldClose = false;
  let interface_ = rl;

  if (!interface_) {
      interface_ = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
      });
      shouldClose = true;
  }

  const answer = await interface_.question(`${question} (y/n): `);

  if (shouldClose) {
      interface_.close();
  }

  return ["y", "yes"].includes(answer.trim().toLowerCase());
}
````

Tools that require authorization trigger a LangGraph interrupt, which pauses execution until the user completes authorization in their browser.

### Create the execution helper

This is a wrapper around the `executeZodTool` function. Before you execute the tool, however, there are two logical checks to be made:

1. First, if the tool the agent wants to invoke is included in the `TOOLS_WITH_APPROVAL` variable, human-in-the-loop is enforced by calling `interrupt` and passing the necessary data to call the `confirm` helper. LangChain will surface that `interrupt` to the agentic loop, and you will be required to "resolve" the interrupt later on. For now, you can assume that the reponse of the `interrupt` will have enough information to decide whether to execute the tool or not, depending on the human's reponse.
2. Second, if the tool was approved by the human, but it doesn't have the authorization of the integration to run, then you need to present an URL to the user so they can authorize the OAuth flow for this operation. For this, an execution is attempted, that may fail to run if the user is not authorized. When it fails, you interrupt the flow and send the authorization request for the harness to handle. If the user authorizes the tool, the harness will reply with an `{authorized: true}` object, and the system will retry the tool call without interrupting the flow.

````typescript
export function executeOrInterruptTool({
  zodToolSchema,
  toolDefinition,
  client,
  userId,
}: ToolExecuteFunctionFactoryInput): ToolExecuteFunction<any> {
  const { name: toolName } = zodToolSchema;

  return async (input: unknown) => {
    try {

      // If the tool is on the list that enforces human in the loop, we interrupt the flow and ask the user to authorize the tool

      if (TOOLS_WITH_APPROVAL.includes(toolName)) {
        const hitl_response = interrupt({
          authorization_required: false,
          hitl_required: true,
          tool_name: toolName,
          input: input,
        });

        if (!hitl_response.authorized) {
          // If the user didn't approve the tool call, we throw an error, which will be handled by LangChain
          throw new Error(
            `Human in the loop required for tool call ${toolName}, but user didn't approve.`
          );
        }
      }

      // Try to execute the tool
      const result = await executeZodTool({
        zodToolSchema,
        toolDefinition,
        client,
        userId,
      })(input);
      return result;
    } catch (error) {
      // If the tool requires authorization, we interrupt the flow and ask the user to authorize the tool
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: toolName,
          user_id: userId,
        });

        // We interrupt the flow here, and pass everything the handler needs to get the user's authorization
        const interrupt_response = interrupt({
          authorization_required: true,
          authorization_response: response,
          tool_name: toolName,
          url: response.url ?? "",
        });

        // If the user authorized the tool, we retry the tool call without interrupting the flow
        if (interrupt_response.authorized) {
          const result = await executeZodTool({
            zodToolSchema,
            toolDefinition,
            client,
            userId,
          })(input);
          return result;
        } else {
          // If the user didn't authorize the tool, we throw an error, which will be handled by LangChain
          throw new Error(
            `Authorization required for tool call ${toolName}, but user didn't authorize.`
          );
        }
      }
      throw error;
    }
  };
}
````

### Create the tool retrieval helper

The last helper function of this module is the `getTools` helper. This function will take the configurations you defined in the `main.ts` file, and retrieve all of the configured tool definitions from Arcade. Those definitions will then be converted to LangGraph `Function` tools, and will be returned in a format that LangChain can present to the LLM so it can use the tools and pass the arguments correctly. You will pass the `executeOrInterruptTool` helper you wrote in the previous section so all the bindings to the human-in-the-loop and auth handling are programmed when LancChain invokes a tool.


````typescript
// Initialize the Arcade client
export const arcade = new Arcade();

export type GetToolsProps = {
  arcade: Arcade;
  toolkits?: string[];
  tools?: string[];
  userId: string;
  limit?: number;
}


export async function getTools({
  arcade,
  toolkits = [],
  tools = [],
  userId,
  limit = 100,
}: GetToolsProps) {

  if (toolkits.length === 0 && tools.length === 0) {
      throw new Error("At least one tool or toolkit must be provided");
  }

  // Todo(Mateo): Add pagination support
  const from_toolkits = await Promise.all(toolkits.map(async (tkitName) => {
      const definitions = await arcade.tools.list({
          toolkit: tkitName,
          limit: limit
      });
      return definitions.items;
  }));

  const from_tools = await Promise.all(tools.map(async (toolName) => {
      return await arcade.tools.get(toolName);
  }));

  const all_tools = [...from_toolkits.flat(), ...from_tools];
  const unique_tools = Array.from(
      new Map(all_tools.map(tool => [tool.qualified_name, tool])).values()
  );

  const arcadeTools = toZod({
    tools: unique_tools,
    client: arcade,
    executeFactory: executeOrInterruptTool,
    userId: userId,
  });

  // Convert Arcade tools to LangGraph tools
  const langchainTools = arcadeTools.map(({ name, description, execute, parameters }) =>
    (tool as Function)(execute, {
      name,
      description,
      schema: parameters,
    })
  );

  return langchainTools;
}
````

## Building the Agent

Back on the `main.ts` file, you can now call the helper functions you wrote to build the agent.

### Retrieve the configured tools

Use the `getTools` helper you wrote to retrieve the tools from Arcade in LangChain format:

````typescript
const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});
````

### Write an interrupt handler

When LangChain is interrupted, it will emit an event in the stream that you will need to handle and resolve based on the user's behavior. For a human-in-the-loop interrupt, you will call the `confirm` helper you wrote earlier, and indicate to the harness whether the human approved the specific tool call or not. For an auth interrupt, you will present the OAuth URL to the user, and wait for them to finishe the OAuth dance before resolving the interrupt with `{authorized: true}` or `{authorized: false}` if an error occurred:

````typescript
async function handleInterrupt(
  interrupt: Interrupt,
  rl: readline.Interface
): Promise<{ authorized: boolean }> {
  const value = interrupt.value;
  const authorization_required = value.authorization_required;
  const hitl_required = value.hitl_required;
  if (authorization_required) {
    const tool_name = value.tool_name;
    const authorization_response = value.authorization_response;
    console.log("⚙️: Authorization required for tool call", tool_name);
    console.log(
      "⚙️: Please authorize in your browser",
      authorization_response.url
    );
    console.log("⚙️: Waiting for you to complete authorization...");
    try {
      await arcade.auth.waitForCompletion(authorization_response.id);
      console.log("⚙️: Authorization granted. Resuming execution...");
      return { authorized: true };
    } catch (error) {
      console.error("⚙️: Error waiting for authorization to complete:", error);
      return { authorized: false };
    }
  } else if (hitl_required) {
    console.log("⚙️: Human in the loop required for tool call", value.tool_name);
    console.log("⚙️: Please approve the tool call", value.input);
    const approved = await confirm("Do you approve this tool call?", rl);
    return { authorized: approved };
  }
  return { authorized: false };
}
````

### Create an Agent instance

Here you create the agent using the `createAgent` function. You pass the system prompt, the model, the tools, and the checkpointer. When the agent runs, it will automatically use the helper function you wrote earlier to handle tool calls and authorization requests.

````typescript
const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});
````

### Write the invoke helper

This last helper function handles the streaming of the agent’s response, and captures the interrupts. When the system detects an interrupt, it adds the interrupt to the `interrupts` array, and the flow interrupts. If there are no interrupts, it will just stream the agent’s to your console.

````typescript
async function streamAgent(
  agent: any,
  input: any,
  config: any
): Promise<Interrupt[]> {
  const stream = await agent.stream(input, {
    ...config,
    streamMode: "updates",
  });
  const interrupts: Interrupt[] = [];

  for await (const chunk of stream) {
    if (chunk.__interrupt__) {
      interrupts.push(...(chunk.__interrupt__ as Interrupt[]));
      continue;
    }
    for (const update of Object.values(chunk)) {
      for (const msg of (update as any)?.messages ?? []) {
        console.log("🤖: ", msg.toFormattedString());
      }
    }
  }

  return interrupts;
}
````

### Write the main function

Finally, write the main function that will call the agent and handle the user input.

Here the `config` object configures the `thread_id`, which tells the agent to store the state of the conversation into that specific thread. Like any typical agent loop, you:

1. Capture the user input
2. Stream the agent's response
3. Handle any authorization interrupts
4. Resume the agent after authorization
5. Handle any errors
6. Exit the loop if the user wants to quit

````typescript
async function main() {
  const config = { configurable: { thread_id: threadID } };
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.green("Welcome to the chatbot! Type 'exit' to quit."));
  while (true) {
    const input = await rl.question("> ");
    if (input.toLowerCase() === "exit") {
      break;
    }
    rl.pause();

    try {
      let agentInput: any = {
        messages: [{ role: "user", content: input }],
      };

      // Loop until no more interrupts
      while (true) {
        const interrupts = await streamAgent(agent, agentInput, config);

        if (interrupts.length === 0) {
          break; // No more interrupts, we're done
        }

        // Handle all interrupts
        const decisions: any[] = [];
        for (const interrupt of interrupts) {
          decisions.push(await handleInterrupt(interrupt, rl));
        }

        // Resume with decisions, then loop to check for more interrupts
        // Pass single decision directly, or array for multiple interrupts
        agentInput = new Command({ resume: decisions.length === 1 ? decisions[0] : decisions });
      }
    } catch (error) {
      console.error(error);
    }

    rl.resume();
  }
  console.log(chalk.red("👋 Bye..."));
  process.exit(0);
}

// Run the main function
main().catch((err) => console.error(err));
````

## Running the Agent

### Run the agent

```bash
bun run main.ts
```

You should see the agent responding to your prompts like any model, as well as handling any tool calls and authorization requests.

## Next Steps

- Clone the [repository](https://github.com/arcade-agents/ts-langchain-E2B) and run it
- Add more toolkits to the `toolkits` array to expand capabilities
- Customize the `systemPrompt` to specialize the agent's behavior
- Explore the [Arcade documentation](https://docs.arcade.dev) for available toolkits

