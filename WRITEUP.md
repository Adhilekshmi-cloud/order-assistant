# Write-up

## Architecture

The app is a single FastAPI service. `tools.py` loads `orders.csv` into memory once and exposes three pure functions. `agent.py` runs the tool-calling loop against the Groq API. `main.py` validates input, maps failures to HTTP errors and serves the static chat page. Using one service means one deployment and no cross-origin setup.

## How the agent decides when to use tools

The model receives three tool schemas whose descriptions say when each applies: `get_order` for a specific order ID, `search_orders` for listing orders, and `aggregate_orders` for counts, totals, averages and rankings. The system prompt lists the valid values of each categorical column, read from the data at startup, so the model maps the user's wording onto real filter values. The loop executes each tool call, feeds the result back, and stops when the model replies in text. For revenue questions the agent makes two calls and reports both the total and the delivered-only figure, because the brief does not say whether cancelled orders count.

## Guardrails

- Messages are limited to 1 to 500 characters and history to 12 turns.
- The model is told never to state a number that did not come from a tool, and never to do arithmetic itself.
- Tools never raise. Bad arguments, unknown filters and missing order IDs return a structured error or "no results" message that the model relays.
- The loop is capped at 5 steps, and calls to the model have a timeout and limited retries.
- Off-topic questions are declined.
- Internal errors are logged on the server and never shown to the user.
- The API key lives only in environment variables.

## Deployment

The app is deployed as a Render free web service built from the GitHub repository, with the API key and model name set as environment variables. Pushing to `main` redeploys it.

## What I would improve with more time

- Streaming responses.
- An evaluation set of questions with known answers, run against the live agent to measure accuracy.
- Per-IP rate limiting.
- Server-side chat history. It is currently stored in the browser only.
- Fuzzy matching on customer names.
- A database instead of an in-memory CSV if the data grew.

## AI tools used

- Claude: ## AI tools used

I used Claude as a pair programmer throughout. It generated most of the code (backend, agent loop, tools, chat UI and tests) from my requirements, and helped me debug setup and deployment issues. I directed the scope and features, ran and tested everything against the dataset, verified the answers by hand, and handled configuration and deployment on Render myself.