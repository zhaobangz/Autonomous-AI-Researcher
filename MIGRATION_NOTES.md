# Migration Notes

## Renamed Files & Folders
- Renamed the `tools ` folder to `tools`.
- Renamed `tools/arvix_search.py` to `tools/arxiv_search.py`.

## New Environment Variables
Added `.env.example` defining the following new variables:
- `OPENAI_API_KEY`: API key for OpenAI LLMs.
- `ANTHROPIC_API_KEY`: API key for Anthropic LLMs.
- `LLM_PROVIDER`: Set to `openai` or `anthropic` to select the underlying LLM provider.
- `LLM_MODEL`: Specifies the target model (e.g., `gpt-4o`).
- `TAVILY_API_KEY`: API key for Tavily Web Search.
- `PINECONE_API_KEY`: API key for Pinecone vector database.
- `VECTOR_BACKEND`: Vector DB backend, either `chroma` or `pinecone`.
- `MAX_STEPS`: The maximum number of agent reasoning steps permitted.

## Breaking Changes
- `core/agent_loop.py` orchestrator function renamed from `agent_loop` to `run_agent`.
- All agents now follow a new explicit tool use protocol and emit events into a queue for UI updates.
- `PythonExecutor` in `tools/code_executor.py` executes directly in the host OS.
- Report generation now produces both a Markdown and PDF file using `weasyprint` and `markdown`.
