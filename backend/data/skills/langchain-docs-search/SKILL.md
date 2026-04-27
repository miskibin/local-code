---
name: langchain-docs-search
description: Search Langchain and LangGraph documentation using the langchain-docs MCP. Load when the user asks about Langchain/LangGraph APIs, concepts, or version-specific behavior you are not certain about.
---

# Langchain / LangGraph docs search

Use the `langchain-docs` MCP tools to look up accurate, version-specific information before answering questions about:

- `langchain`, `langchain-core`, `langchain-community` APIs
- `langgraph` graph construction, nodes, edges, state, checkpointers
- `langchain-openai`, `langchain-anthropic`, `langchain-ollama` integrations
- `langchain-mcp-adapters` and other ecosystem packages

**Never hallucinate API signatures, parameter names, or class hierarchies.** If uncertain, search first.

## When to search

| Signal | Action |
|--------|--------|
| User asks "how do I use X in LangGraph" | Search before answering |
| User pastes a deprecation warning or error | Search the affected symbol |
| You're unsure about a parameter name/default | Search the class or function |
| User asks about a feature added after 2024 | Always search — training data may be stale |

## Query patterns

Good queries are specific: library + symbol + what you need.

```
# Good
"LangGraph StateGraph add_node signature"
"langchain-core RunnableConfig configurable fields"
"LangGraph AsyncSqliteSaver from_conn_string"
"langchain-ollama ChatOllama streaming"

# Too vague
"langchain"
"how does langchain work"
```

## Typical flow

1. Call the docs search tool with a specific query.
2. Read the returned excerpts — prefer the official API reference over guides when you need exact signatures.
3. Cite the relevant doc section in your reply so the user can follow up.
4. If the first result is insufficient, refine the query (add version, narrow the symbol name).

## Do not use for

- General Python questions unrelated to the Langchain ecosystem.
- Questions the user has already answered with their own code snippet.
- Chinook / SQL questions — use `sql-agent` for those.
