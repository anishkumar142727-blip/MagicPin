# MagicPin AI Challenge - Vera Assistant

## Approach
This solution is built using a modern **FastAPI** web server and **LangChain** with the `gemini-flash-latest` model. 
It utilizes a single-prompt composer with context retrieval, dynamically ingesting the `CategoryContext`, `MerchantContext`, and `TriggerContext` directly into the LLM's system prompt.

The application is deployed to **Vercel** for serverless, low-latency execution.

## Extra Credit: Multi-turn Conversations & Intent Transitions
I fully implemented the `/v1/reply` endpoint with stateful conversation tracking. 
- **Auto-reply detection**: The LLM is instructed to detect standard auto-replies and gracefully exit to save engagement turns.
- **Intent transitions**: When a merchant replies positively (e.g. "Let's do it"), the model immediately drops the pitch framing and shifts to an action-oriented "YES/STOP" or "open-ended" CTA.

## Tradeoffs
- **In-memory State**: For the sake of this challenge, `contexts` and `conversations` are stored in-memory dictionaries. In a true production environment, these would be persisted to Redis or PostgreSQL.
- **Latency**: To meet the <30s constraint, I opted for Gemini Flash over larger models, which perfectly balances incredible speed with strong reasoning capabilities for merchant tone-matching.

## How to Test
The backend is live at: `https://magic-pin-three.vercel.app`
