#!/usr/bin/env python3
"""
Simple agent server without reload for debugging
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
import os
import sys

# Add chatbot path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

print("Starting simple agent server...")

# Import agent
try:
    from agents.agent import root_agent
    AGENT_AVAILABLE = True
    print(f"SUCCESS: Agent imported - {root_agent.name}")
except ImportError as e:
    AGENT_AVAILABLE = False
    print(f"ERROR: Agent import failed - {e}")

app = FastAPI(title="Career Assistant API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("FastAPI app created")

# Models
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: str = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    user_id: str
    agent: str
    model: str

print("Models defined")

@app.get("/")
async def root():
    print("Root endpoint called")
    return {
        "service": "Career Assistant API",
        "status": "running" if AGENT_AVAILABLE else "agent not available",
        "agent": root_agent.name if AGENT_AVAILABLE else "none",
        "model": root_agent.model if AGENT_AVAILABLE else "none"
    }

@app.get("/health")
async def health():
    print("Health endpoint called")
    return {
        "status": "healthy" if AGENT_AVAILABLE else "unhealthy",
        "agent_available": AGENT_AVAILABLE,
        "model": root_agent.model if AGENT_AVAILABLE else None
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Simple chat endpoint"""
    print(f"Chat endpoint called with message: {request.message}")
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    return {
        "response": f"Echo: {request.message}",
        "session_id": "test_session",
        "user_id": request.user_id,
        "agent": root_agent.name,
        "model": root_agent.model
    }

print("All endpoints defined")

if __name__ == "__main__":
    print("Starting uvicorn server without reload...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )