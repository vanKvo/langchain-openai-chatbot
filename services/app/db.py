"""
Database configuration and utilities for MongoDB
"""
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.environ.get("MONGODB_DATABASE", "chatbot_db")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Collections
conversations = db.conversations
messages = db.messages

# Ensure indexes for better query performance
async def create_indexes():
    # Index for conversations by user_id and creation date
    await conversations.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    # Index for messages by conversation_id and timestamp
    await messages.create_index([("conversation_id", ASCENDING), ("timestamp", ASCENDING)])

async def get_or_create_conversation(user_id: str, session_id: str):
    """Get existing conversation or create a new one"""
    conversation = await conversations.find_one({
        "user_id": user_id,
        "session_id": session_id
    })
    
    if not conversation:
        conversation = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await conversations.insert_one(conversation)
        conversation["_id"] = result.inserted_id
    
    return conversation

async def save_message(conversation_id, role: str, content: str):
    """Save a message to the database"""
    message = {
        "conversation_id": conversation_id,
        "role": role,  # 'user' or 'assistant'
        "content": content,
        "timestamp": datetime.utcnow()
    }
    await messages.insert_one(message)

async def get_conversation_history(conversation_id, limit: int = 50):
    """Get messages from a conversation"""
    cursor = messages.find({"conversation_id": conversation_id}) \
                    .sort("timestamp", ASCENDING) \
                    .limit(limit)
    return [msg async for msg in cursor]

async def get_user_conversations(user_id: str, skip: int = 0, limit: int = 20):
    """Get list of conversations for a user"""
    cursor = conversations.find({"user_id": user_id}) \
                         .sort("updated_at", DESCENDING) \
                         .skip(skip) \
                         .limit(limit)
    return [conv async for conv in cursor]