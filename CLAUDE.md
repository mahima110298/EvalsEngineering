# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A conversational todo list agent built on top of Ollama's local LLM inference. The agent understands natural language commands and manages an in-memory todo list via tool calling.

**Runtime dependency:** Ollama must be running locally with the `gemma4:e2b-it-q4_K_M` model pulled.

## Setup & Running

```bash
# Install the Ollama Python client
pip install ollama

# Pull the model (one-time)
ollama pull gemma4:e2b-it-q4_K_M

# Run the agent
python todo_agent.py
```

**In-session commands:** type `list` to display all todos, `quit` to exit.

## Architecture

Everything lives in `todo_agent.py`. The key layers:

**State** — Two globals: `todos` (list of dicts) and `next_id` (auto-increment counter). No persistence; state resets on restart.

**Tools** — Six callable functions: `add`, `edit`, `delete`, `complete`, `ask_clarification`, `confirm`. Their JSON schemas (lines 89–188) are passed to Ollama in OpenAI tool-call format. The model decides which tool(s) to invoke.

**Agentic loop** (`run_agent`, lines 199–240) — Maintains a rolling message history. On each turn it sends the full history + tools to Ollama, then processes any tool calls (executing them and appending results), repeating until the model returns a plain text response with no tool calls.

**Safety rules baked into the system prompt** — The agent must call `confirm` before any delete, and `ask_clarification` for ambiguous requests. It must never fabricate todo IDs.

## Key Design Decisions

- The model is invoked in a `while True` loop inside `run_agent` — it only exits when `response.message.tool_calls` is falsy, meaning the model has finished reasoning.
- Tool results are appended as `role: tool` messages before the next model call, following Ollama's multi-turn tool protocol.
- `ask_clarification` pauses the loop to collect user input mid-turn (not just at the top-level REPL), allowing nested clarification within a single user request.
