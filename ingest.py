#!/usr/bin/env python3
"""
ingest.py
- Loads text files from ./docs
- Splits into chunks
- Creates embeddings using OpenAIEmbeddings (via LangChain)
- Stores them in a Chroma vectorstore persisted to disk
"""
import os
from dotenv import load_dotenv
#from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
#from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
#from langchain.vectorstores import Chroma
from langchain_community.vectorstores import Chroma

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")

if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in environment or .env file")

# 1) Load documents from docs/ (one or more .txt, .md files)
loader = DirectoryLoader("docs", glob="**/*.*", loader_cls=TextLoader)
docs = loader.load()
print(f"Loaded {len(docs)} documents")

# 2) Split into chunks suitable for embeddings
# Recursive character-based chunking (also called hierarchical text splitting).
# RecursiveCharacterTextSplitter - Splits intelligently by going through different levels of separators 
# (like paragraphs, sentences, words, etc.) until each piece fits within your desired size.
# Each chunk will aim to have up to 1000 characters.
# Each new chunk will overlap the previous one by 200 characters. This overlap helps preserve context continuity 
# between chunks so the embedding model doesn’t lose meaning at the chunk boundaries.
# Result: Get a list of text chunks (each ~1000 characters, overlapping by 200), 
# ready to feed into a vector store
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200) 
chunks = splitter.split_documents(docs)
print(f"Created {len(chunks)} chunks")

# 3) Create embeddings and persist with Chroma
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=PERSIST_DIR,
)
vectorstore.persist()
print(f"Persisted vectorstore to {PERSIST_DIR}")
