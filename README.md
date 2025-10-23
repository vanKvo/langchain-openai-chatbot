# LangChain + OpenAI Context-aware Chatbot

This repository contains a minimal example integrating OpenAI + LangChain to build a context-aware chatbot for customer inquiries. It includes:
- ingest.py: ingest docs into Chroma vector store
- app.py: FastAPI chat server exposing /chat
- auth_service.py: auth services
- db.py: MongoDB database storing chat conversations
- a minimal static UI in ui/index.html
- prompt_template.md: example system prompt
- requirements.txt and .env.example
- docker-compose.yml: orchestra all microservices.

Quickstart (local)
1. Clone or create the repo locally and add these files.

2. Create a Python virtual env and install dependencies:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. Create a .env file from .env.example and set OPENAI_API_KEY.

4. Add docs to the `docs/` folder (text or markdown). Then run:
   python ingest.py

5. Run docker-compose.yml to start the database and backend services.

6. Open the minimal UI:
   Serve the ui folder:
   python -m http.server --directory ui 8080
   Then visit http://localhost:8080

Notes and production tips
- Session memory in this example is in-memory. For production use Redis or a DB.
- Chroma is fine for small projects; for scale consider Pinecone, Weaviate, or Milvus.
- Scrub PII before storing or sending user data to external APIs.
- To lower costs, use a cheaper model for initial responses or reranking.
