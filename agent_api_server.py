from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

app = FastAPI(
    title="Career Assistant API",
    description="Agent Server for Job Sphere Chatbot",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"
    context: Optional[dict] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    source: str = "agent_api_server"
    metadata: Optional[dict] = None

# Simple in-memory storage for conversations
conversations = {}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agent_api_server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agent API Server",
        "status": "running",
        "endpoints": {
            "POST /api/chat": "Send message to agent",
            "GET /health": "Health check"
        }
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        logger.info(f"Received message from {request.user_id}: {request.message[:100]}...")
        
        # Store conversation context
        user_key = request.user_id
        if user_key not in conversations:
            conversations[user_key] = []
        
        conversations[user_key].append({
            "timestamp": datetime.now().isoformat(),
            "user": request.message,
            "context": request.context or {}
        })
        
        # Generate response
        response_text = generate_agent_response(request.message, request.context or {})
        
        # Add to conversation history
        conversations[user_key].append({
            "timestamp": datetime.now().isoformat(),
            "agent": response_text
        })
        
        # Keep only last 20 messages
        if len(conversations[user_key]) > 20:
            conversations[user_key] = conversations[user_key][-20:]
        
        return ChatResponse(
            response=response_text,
            source="agent_api_server",
            metadata={
                "user_id": request.user_id,
                "session_id": request.session_id,
                "message_length": len(request.message),
                "response_length": len(response_text),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_agent_response(message: str, context: Dict[str, Any]) -> str:
    """Generate intelligent response based on message and context"""
    message_lower = message.lower()
    
    # Simple rule-based responses
    if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "greetings"]):
        return "Hello! I'm your career assistant. How can I help you today?"
    
    elif "job" in message_lower and "recommend" in message_lower:
        skills = context.get("skills", "")
        if "python" in skills.lower():
            return "Based on your Python skills, I recommend roles like:\n1. Python Developer\n2. Data Scientist\n3. Backend Engineer\n4. DevOps Engineer\n\nWould you like more specific advice?"
        return "I recommend exploring roles in Software Development, Data Analysis, or Cloud Engineering. Could you share more about your skills?"
    
    elif "resume" in message_lower:
        return "For resume advice:\n1. Use action verbs\n2. Quantify achievements\n3. Tailor to job description\n4. Keep it 1-2 pages\n5. Include relevant keywords"
    
    elif "interview" in message_lower:
        return "Interview tips:\n1. Research the company\n2. Practice common questions\n3. Prepare STAR method examples\n4. Ask insightful questions\n5. Follow up afterwards"
    
    elif "salary" in message_lower:
        return "For salary negotiation:\n1. Research market rates\n2. Know your minimum\n3. Consider total compensation\n4. Practice your pitch\n5. Be confident but flexible"
    
    elif "skill" in message_lower:
        return "Important skills to develop:\n1. Technical skills in your field\n2. Communication skills\n3. Problem-solving\n4. Adaptability\n5. Continuous learning"
    
    else:
        return f"I understand you're asking about: {message}\n\nI can help with:\n• Job recommendations\n• Resume optimization\n• Interview preparation\n• Career advice\n• Salary guidance\n\nWhat specific help do you need?"

@app.post("/chat")
async def legacy_chat(request: dict):
    """Legacy chat endpoint for backward compatibility"""
    try:
        # Convert to new format
        chat_request = ChatRequest(
            message=request.get('message', ''),
            user_id=request.get('user_id', 'anonymous'),
            session_id=request.get('session_id')
        )
        
        return await chat(chat_request)
        
    except Exception as e:
        logger.error(f"Error in legacy chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Agent API Server on port {port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"Chat endpoint: POST http://localhost:{port}/api/chat")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )