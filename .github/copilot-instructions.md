# mem0Chatbot Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-30

## Active Technologies

- Python 3.12 + FastAPI, Mem0, Google Generative AI SDK (Gemini 2.5 Flash), Google AI Python SDK (Embeddings), ChromaDB, SQLite3, Pydantic (001-mem0-investment-advisor)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.12: Follow standard conventions

## Recent Changes

- 001-mem0-investment-advisor: Added Python 3.12 + FastAPI, Mem0, Google Generative AI SDK (Gemini 2.5 Flash), Google AI Python SDK (Embeddings), ChromaDB, SQLite3, Pydantic

<!-- MANUAL ADDITIONS START -->
# Copilot Commit Message Policy

Please always generate commit messages using **Conventional Commits** format:

`<type>(<scope>): <short summary>`

Example:
- feat(memory): add persistent session cache
- fix(api): handle empty response gracefully
- refactor(ui): simplify chat message rendering logic
<!-- MANUAL ADDITIONS END -->
