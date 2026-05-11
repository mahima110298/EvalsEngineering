import json
import ollama
from datetime import datetime

MODEL = "gemma4:e2b-it-q4_K_M"

todos = []
next_id = 1

ALLOWED_ACTIONS = ["add", "edit", "delete", "complete", "ask_clarification", "confirm"]


def get_todos_display() -> str:
    if not todos:
        return "No todos yet."
    lines = []
    for todo in todos:
        status = "✓" if todo["completed"] else "○"
        desc = f" — {todo['description']}" if todo["description"] else ""
        lines.append(f"  [{todo['id']}] {status} {todo['title']}{desc}")
    return "\n".join(lines)


# --- Tool implementations ---

def add(title: str, description: str = "") -> dict:
    global next_id
    todo = {
        "id": next_id,
        "title": title,
        "description": description,
        "completed": False,
        "created_at": datetime.now().isoformat(),
    }
    todos.append(todo)
    next_id += 1
    return {"success": True, "id": todo["id"], "message": f"Added todo #{todo['id']}: '{title}'"}


def edit(id: int, title: str = None, description: str = None) -> dict:
    for todo in todos:
        if todo["id"] == id:
            if title is not None:
                todo["title"] = title
            if description is not None:
                todo["description"] = description
            return {"success": True, "todo": todo, "message": f"Updated todo #{id}"}
    return {"success": False, "message": f"Todo #{id} not found"}


def delete(id: int) -> dict:
    for i, todo in enumerate(todos):
        if todo["id"] == id:
            removed = todos.pop(i)
            return {"success": True, "message": f"Deleted todo #{id}: '{removed['title']}'"}
    return {"success": False, "message": f"Todo #{id} not found"}


def complete(id: int) -> dict:
    for todo in todos:
        if todo["id"] == id:
            todo["completed"] = True
            return {"success": True, "message": f"Marked todo #{id} as complete: '{todo['title']}'"}
    return {"success": False, "message": f"Todo #{id} not found"}


def ask_clarification(question: str) -> dict:
    print(f"\nAgent needs clarification: {question}")
    answer = input("You: ").strip()
    return {"clarification": answer}


def confirm(action_description: str) -> dict:
    print(f"\nAgent: Confirm — {action_description}? (yes/no)")
    answer = input("You: ").strip().lower()
    confirmed = answer in ("yes", "y")
    return {"confirmed": confirmed, "message": "Confirmed." if confirmed else "Cancelled."}


TOOL_HANDLERS = {
    "add": add,
    "edit": edit,
    "delete": delete,
    "complete": complete,
    "ask_clarification": ask_clarification,
    "confirm": confirm,
}

# --- Tool schemas (Ollama/OpenAI format) ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add a new todo item to the list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the todo item"},
                    "description": {"type": "string", "description": "Optional longer description"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Edit the title or description of an existing todo item by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID of the todo to edit"},
                    "title": {"type": "string", "description": "New title (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete",
            "description": "Delete a todo item by its ID. Always use confirm first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID of the todo to delete"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete",
            "description": "Mark a todo item as completed by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID of the todo to mark as complete"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": (
                "Ask the user a clarifying question when their request is ambiguous "
                "(e.g. they say 'delete it' without specifying which item)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question to ask"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm",
            "description": (
                "Ask the user to confirm a destructive or important action before executing it. "
                "Always call this before delete."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_description": {
                        "type": "string",
                        "description": "Human-readable description of the action to confirm",
                    },
                },
                "required": ["action_description"],
            },
        },
    },
]


def process_tool_call(name: str, args: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown action: {name}"})
    result = handler(**args)
    return json.dumps(result)


def run_agent(user_message: str) -> None:
    system_content = (
        f"You are a concise, helpful todo list assistant.\n\n"
        f"Current todos:\n{get_todos_display()}\n\n"
        f"Allowed actions: {ALLOWED_ACTIONS}\n\n"
        "Rules:\n"
        "- Always call confirm before delete.\n"
        "- Call ask_clarification when the request is ambiguous (missing ID, unclear item, etc.).\n"
        "- After completing an action, briefly summarize what you did.\n"
        "- Do not hallucinate todo IDs — only reference IDs that exist in the list above."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message},
    ]

    while True:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        msg = response.message
        # Append the assistant turn (including any tool_calls) to history
        messages.append(msg)

        if not msg.tool_calls:
            # No tools called — final text reply
            if msg.content:
                print(f"\nAgent: {msg.content}")
            break

        # Execute each tool call and feed results back
        for tc in msg.tool_calls:
            name = tc.function.name
            # ollama returns arguments as a dict
            args = tc.function.arguments if isinstance(tc.function.arguments, dict) else json.loads(tc.function.arguments)
            print(f"  [tool: {name}]")
            result = process_tool_call(name, args)
            messages.append({"role": "tool", "content": result, "name": name})


def main():
    print("=" * 45)
    print(f"    Todo List Agent  [{MODEL}]")
    print("=" * 45)
    print("Type your request in plain English.")
    print("Type 'list' to show todos, 'quit' to exit.")
    print("=" * 45)

    while True:
        print()
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if user_input.lower() in ("list", "ls"):
            print("\nCurrent Todos:")
            print(get_todos_display())
            continue

        run_agent(user_input)


if __name__ == "__main__":
    main()
