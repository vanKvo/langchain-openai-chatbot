#!/usr/bin/env python3
"""
app.py
- FastAPI server exposing /chat and /health endpoints
- Uses LangChain ConversationalRetrievalChain backed by OpenAI LLM + Chroma retriever
- Per-session ConversationBufferMemory (in-memory). For production, replace with Redis/DB-backed memory.
- Delegates token verification to auth_service.py microservice
"""
import os
import uuid
from typing import Optional, List
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status, Header
import requests
from db import get_or_create_conversation, save_message, get_conversation_history, create_indexes
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# Load env
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR")
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-5-nano")
#MODEL_NAME = os.environ.get("OPENAI_MODEL")

# Auth service URL (auth microservice)
AUTH_SERVICE_VERIFY_URL = os.environ.get("AUTH_SERVICE_VERIFY_URL", "http://0.0.0.0:8001/verify")


app = FastAPI(title="Customer Chatbot API")

# List of the origins (URLs) allowed to make requests to the FastAPI app
origins = [
    "http://localhost:8081"  # Your frontend running on localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Allow requests from the specified origins
    allow_credentials=True, # Allow cookies, authorization headers, etc. including in cross-origin requests
    allow_methods=["POST", "GET"],  # Only allow necessary methods
    allow_headers=["Authorization", "Content-Type"],  # Only allow necessary headers
)

# Event handler to create MongoDB indexes on startup
@app.on_event("startup")
async def startup_event():
    await create_indexes()

# BaseModel from Pydantic provides automated data validation, error checking, serialization/deserialization (Python <-> JSON), 
# and clear structure for API interactions.
# Data validation: It check whether data matches the types and constraints you defined.
# if the data is valid, Pydantic returns an instance of your model with the data. 
# if not, it provides a detailed error message.
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str

class ChatResponse(BaseModel):
    session_id: str
    answer: str

# Verify token by delegating to auth microservice
def verify_token_with_auth_service(authorization: Optional[str]):
    """Call the auth service /verify endpoint to validate the Bearer token.
    Returns the username if valid, otherwise raises HTTPException.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    try:
        resp = requests.get(AUTH_SERVICE_VERIFY_URL, headers={"Authorization": authorization}, timeout=5)
        #resp = verify_token(authorization)
    except requests.RequestException:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth service unavailable")
   
    # Converts JSON into a Python dict via .json().
    data = resp.json()

    if resp.status_code != 200:
        # Bubble up auth errors
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return data.get("username")

def get_chain():
    # LLM
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=1, openai_api_key=OPENAI_API_KEY)

    # embeddings + vectorstore retriever (Chroma persisted by ingest.py)
    # OpenAIEmbeddings - This object is responsible for converting text into 
    # numerical vector representations (embeddings) using OpenAI's embedding models.
    # Chroma - An open-source, lightweight vector database used for storing and querying vector embeddings. 
    # persist_directory=PERSIST_DIR - the local directory where the Chroma database will store its data, 
    # allowing it to persist between sessions.
    # embedding_function=embeddings - Ensure that any text added to the vector store will be embedded using the specified OpenAI model.
    # retriever - an object fetches relevant data based in a given query
    # typically by performing a similarity search on the stored embeddings.
    # search_type="mmr" -  Maximal Marginal Relevance (MMR), a search algorithm retrieve documents 
    # that are both relevant to the query and diverse, reducing redundancy in the search results.
    # k=6 indicates that the retriever should return the top 6 most relevant and diverse documents based on the MMR algorithm.
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 6})

    # ConversationalRetrievalChain handles retrieval + combine: 
    # A conversational AI that can retrieve info from a knowledge base and provide context-aware answers.
    # When a new question is asked in the context of a conversation, the chain first uses an LLM (typically the same llm provided, or a separate one if configured) 
    # to rephrase the current question, taking into account the chat history. 
    # The rephrased question is then passed to the retriever to retrieve relevant documents 
    # from the knowledge base.(e.g., a vector store) based on a given query.
    # return_source_documents instructs the chain to return the source documents that were used to generate the answer, 
    # in addition to the answer itself. This is useful for transparency and debugging.
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm, 
        retriever=retriever, 
        return_source_documents=True, 
    )
    # The retrieved documents, along with the original question (or the rephrased one), 
    # are then passed to another internal chain to synthesizes an answer based on 
    # the provided context and the question.
    return chain 

@app.get("/health")
async def health():
    return {"status": "ok"}

def _extract_authorization(authorization: Optional[str] = Header(None)):
    return authorization

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: Optional[str] = Depends(_extract_authorization)):
    # verify token with external auth service
    current_user = verify_token_with_auth_service(authorization)
    
    # Get or create conversation in MongoDB
    session_id = req.session_id or str(uuid.uuid4())
    conversation = await get_or_create_conversation(current_user, session_id)
    
    # Get chat history from MongoDB
    messages = await get_conversation_history(conversation["_id"])
    chat_history = [(msg["content"], msg["content"]) for msg in messages if msg["role"] in ["user", "assistant"]]

    chain = get_chain()
    
    inputs = {
        "question": req.question,
        "chat_history": chat_history
    }

    # Get response from LangChain
    result = chain(inputs)
    answer = result.get("answer") or result.get("output_text") or ""
    if not answer:
        raise HTTPException(status_code=500, detail="No answer from chain")

    # Save messages to MongoDB
    await save_message(conversation["_id"], "user", req.question)
    await save_message(conversation["_id"], "assistant", answer)

    return ChatResponse(session_id=session_id, answer=answer)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8090, reload=True)
