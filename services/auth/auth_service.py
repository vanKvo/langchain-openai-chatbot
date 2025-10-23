#!/usr/bin/env python3
"""
auth_service.py
- FastAPI auth microservice providing /token and /verify endpoints
- Creates short-lived JWTs and verifies them
- Demo-only: uses an in-memory demo user. Replace with a proper user DB in production.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here") # JWT signing key
ALGORITHM = "HS256" # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo user - replace with database in production
DEMO_USER = {
    "username": os.environ.get("DEMO_USERNAME", "demo"),
    "hashed_password": pwd_context.hash(os.environ.get("DEMO_PASSWORD", "demo-password"))
}

app = FastAPI(title="Auth Service")

# List of the origins (URLs) allowed to make requests to the FastAPI app
origins = [
    "http://localhost:8081",  # Your frontend running on localhost
    "http://127.0.0.1:8090"   # Local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Allow requests from the specified origins
    allow_credentials=True, # Allow cookies, authorization headers, etc. including in cross-origin requests
    allow_methods=["POST", "GET"],  # Only allow necessary methods
    allow_headers=["Authorization", "Content-Type"],  # Only allow necessary headers
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy() # Copy input data to avoid mutation. User payload data.
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Very small demo check - replace with DB + proper checks
    if form_data.username != DEMO_USER["username"] or not pwd_context.verify(form_data.password, DEMO_USER["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

def _extract_authorization(authorization: Optional[str] = Header(None)):
    return authorization

@app.get("/verify")
def verify_token(authorization: Optional[str] = Header(None)):
    """Verify Authorization header `Bearer <token>` and return username if valid."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print("Username:", username)
        if username is None:
            raise JWTError()
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"username": username}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("auth_service:app", host="0.0.0.0", port=8001, reload=True)
