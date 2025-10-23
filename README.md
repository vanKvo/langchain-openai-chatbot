# LangChain + OpenAI Context-aware Chatbot

This repository contains a minimal example integrating OpenAI + LangChain to build a context-aware chatbot for customer inquiries. It includes:
- ingest.py: ingest docs into Chroma vector store
- app.py: FastAPI chat server exposing /chat
- a minimal static UI in ui/index.html
- prompt_template.md: example system prompt
- requirements.txt and .env.example

Quickstart (local)
1. Clone or create the repo locally and add these files.
2. Create a Python virtual env and install dependencies:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. Create a .env file from .env.example and set OPENAI_API_KEY.

4. Add docs to the `docs/` folder (text or markdown). Then run:
   python ingest.py

Option 1:
Serve UI and backend in the same port (testing)
5. This code below added into app.py will mount the ui to the root of the backend server.
app.mount("/ui", StaticFiles(directory="ui"), name="ui")
@app.get("/")
def root():
    return FileResponse("ui/index.html")
6. Start the API:
   python app.py
    
Option 2 (recommeded in prod):
Serve backend and UI in different ports. Need to make sure the backend server (app.py) allows CORS.
5. In the main app, allows CORS.
from fastapi.middleware.cors import CORSMiddleware
# List of the origins (URLs) allowed to make requests to the FastAPI app
origins = [
        "http://localhost:8081",  # Your frontend running on localhost
    ] 
app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # List of allowed origins. Use a regex string with allow_origin_regex for more complex matching.
        allow_credentials=True,  # Allow creds like cookies, HTTP authentication, and client-side SSL certificates to be sent with cross-origin requests
        allow_methods=["*"],  # Allow all standard HTTP methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # Allow all headers
    )

6. Start the API:
   python app.py
   # or: uvicorn app:app --reload

7. Open the minimal UI:
   Serve the ui folder:
   python -m http.server --directory ui 8080 # http. server is a built-in module that allows you to create a simple HTTP server to serve files from a directory
   Then visit http://localhost:8080

Notes and production tips
- Session memory in this example is in-memory. For production use Redis or a DB.
- Chroma is fine for small projects; for scale consider Pinecone, Weaviate, or Milvus.
- Scrub PII before storing or sending user data to external APIs.
- To lower costs, use a cheaper model for initial responses or reranking.
