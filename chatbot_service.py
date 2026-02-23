import requests
import json
import os
import sys
import uuid
from typing import Dict, Any, Optional
import logging

# Add to chatbot_service.py imports
try:
    from services.gemini_agent_service import gemini_agent_service
    GEMINI_AGENT_AVAILABLE = True
except ImportError as e:
    GEMINI_AGENT_AVAILABLE = False

# Import AI agent service
try:
    from services.job_ai_agent_service import job_ai_agent_service
    AI_AGENT_AVAILABLE = True
except ImportError as e:
    AI_AGENT_AVAILABLE = False

# Configure logging to handle unicode characters
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self):
        self.agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:8000')
        self.use_agent_server = True
        self.use_ai_agent = AI_AGENT_AVAILABLE
        self.use_gemini_agent = GEMINI_AGENT_AVAILABLE
        
        # Priority order
        self.response_priority = ['agent_server', 'gemini', 'ai_agent', 'mock']
        
        # Add missing attributes for status endpoint
        self.agent_name = "JobSphere Assistant"
        self.adk_base_url = os.environ.get('ADK_BASE_URL', 'http://localhost:8000')
        
        logger.info(f"ChatbotService initialized")
        logger.info(f"Response priority: {self.response_priority}")
        logger.info(f"Agent server URL: {self.agent_server_url}")
        
        self.user_contexts = {}  # Store user contexts for personalization
        self.session_id = str(uuid.uuid4())  # Generate a default session ID
        
    def _call_agent_server(self, message: str, user_id: str = None, 
                          user_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Call the agent server for processing"""
        try:
            logger.info(f"Calling agent server at: {self.agent_server_url}")
            
            # Prepare the request payload matching agent_api_server format
            payload = {
                "message": message,
                "user_id": user_id or "anonymous",
                "session_id": self.session_id
            }
            
            # Add context if provided
            if user_context:
                payload["context"] = user_context
            
            logger.info(f"Sending payload to agent server: {json.dumps(payload, indent=2)}")
            
            # Make request to agent server
            response = requests.post(
                f"{self.agent_server_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            logger.info(f"Agent server response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Agent server response received successfully")
                
                # Extract response based on actual response structure
                if "response" in data:
                    response_content = data["response"]
                elif "content" in data:
                    response_content = data["content"]
                else:
                    response_content = str(data)
                
                return {
                    "content": response_content,
                    "source": "agent_server",
                    "metadata": data.get("metadata", {})
                }
            else:
                logger.error(f"Agent server error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.warning("Agent server is not reachable. Make sure it's running.")
            return None
        except requests.exceptions.Timeout:
            logger.warning("Agent server request timed out")
            return None
        except Exception as e:
            logger.error(f"Error calling agent server: {str(e)}")
            return None
    
    def send_message(self, message: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Send message to chatbot with multi-provider fallback"""
        logger.info(f"Processing message: '{message[:100]}...'")
        
        # Extract user ID from message if not provided
        original_message = message
        if not user_id and message.startswith("[User ID:"):
            try:
                end_idx = message.find("]")
                if end_idx != -1:
                    user_id = message[9:end_idx].strip()
                    message = message[end_idx + 1:].strip()
                    logger.info(f"Extracted user_id from message: {user_id}")
            except Exception as e:
                logger.warning(f"Error extracting user_id: {e}")
        
        # Get user context
        user_context = self.user_contexts.get(user_id, {}) if user_id else {}
        
        # 1. TRY AGENT SERVER FIRST
        if self.use_agent_server:
            logger.info("Trying Agent Server...")
            try:
                agent_response = self._call_agent_server(message, user_id, user_context)
                if agent_response and agent_response.get("content"):
                    logger.info(f"Agent Server response received: {len(agent_response['content'])} chars")
                    return agent_response
                else:
                    logger.warning("Agent Server returned no content")
            except Exception as e:
                logger.error(f"Agent Server failed: {str(e)}")
        
        # 2. TRY GEMINI AGENT (for Indian career advice)
        if self.use_gemini_agent and self._is_indian_career_query(message):
            logger.info("Trying Gemini agent...")
            try:
                response = gemini_agent_service.get_response(message, user_id, user_context)
                if response:
                    logger.info(f"Gemini response received: {len(response)} chars")
                    return {"content": response, "source": "gemini"}
            except Exception as e:
                logger.error(f"Gemini agent failed: {str(e)}")
        
        # 3. TRY AI AGENT
        if self.use_ai_agent:
            logger.info("Trying AI agent...")
            try:
                ai_response = job_ai_agent_service.get_ai_response(message, user_id=user_id, context=user_context)
                if ai_response:
                    if isinstance(ai_response, dict):
                        content = ai_response.get('content')
                        if content:
                            logger.info(f"AI agent response received: {len(content)} chars")
                            return {"content": content, "source": "ai_agent"}
                    else:
                        content_str = str(ai_response)
                        if content_str:
                            logger.info(f"AI agent response received: {len(content_str)} chars")
                            return {"content": content_str, "source": "ai_agent"}
            except Exception as e:
                logger.error(f"AI agent failed: {str(e)}")
        
        # FINAL FALLBACK - Mock response
        logger.warning("All AI providers failed, using mock response")
        return self._get_mock_response(message)
    
    def _get_mock_response(self, message: str) -> Dict[str, Any]:
        """Generate a mock response for testing purposes"""
        message_lower = message.lower()
        
        # Check for greeting keywords
        words = message_lower.split()
        has_hello = "hello" in words
        has_hi = "hi" in words
        has_hey = "hey" in words
        
        # Check for job-related keywords
        job_keywords = ["job", "recommend", "career", "resume", "interview", "skill", "salary"]
        has_job_query = any(keyword in message_lower for keyword in job_keywords)
        
        if has_hello or has_hi or has_hey:
            return {
                "content": "Hello! I'm your Job Sphere assistant. How can I help you today? I can provide job recommendations, interview tips, and resume advice.",
                "source": "mock"
            }
        elif "interview" in message_lower and "tip" in message_lower:
            return {
                "content": "Here are essential interview tips:\n1. Research the company thoroughly\n2. Practice common interview questions\n3. Prepare examples of your achievements\n4. Dress professionally\n5. Ask thoughtful questions",
                "source": "mock"
            }
        elif "resume" in message_lower:
            return {
                "content": "Resume optimization tips:\n1. Keep it concise (1-2 pages)\n2. Use action verbs\n3. Quantify achievements\n4. Tailor for each job\n5. Include keywords from job description",
                "source": "mock"
            }
        elif "skill" in message_lower or "learn" in message_lower:
            return {
                "content": "In-demand skills:\n1. Programming languages\n2. Cloud computing\n3. Data analysis\n4. Communication skills\n5. Problem-solving",
                "source": "mock"
            }
        elif has_job_query:
            return {
                "content": "Based on your query, here are job recommendations:\n\n1. Software Developer - High demand for Python/JavaScript skills\n2. Data Analyst - Growing field with good opportunities\n3. Full Stack Engineer - Combines frontend and backend skills\n\nWould you like more specific recommendations?",
                "source": "mock"
            }
        else:
            return {
                "content": "I'm here to help with your career journey! I can assist with:\n1. Job recommendations\n2. Resume optimization\n3. Interview preparation\n4. Career advice\n5. Skill development\n\nWhat would you like help with today?",
                "source": "mock"
            }
    
    def get_job_recommendations(self, user_profile: Dict[str, Any], user_id: str = None) -> Optional[str]:
        """Get job recommendations based on user profile"""
        if user_id:
            self.user_contexts[user_id] = user_profile
        
        # Create a prompt from user profile
        prompt = f"Provide job recommendations for someone with skills: {user_profile.get('skills', 'Not specified')}, "
        prompt += f"experience: {user_profile.get('experience', 'Not specified')}, "
        prompt += f"education: {user_profile.get('education', 'Not specified')}, "
        prompt += f"and preferences: {user_profile.get('preferences', 'Not specified')}"
        
        response = self.send_message(prompt, user_id)
        if response and 'content' in response:
            return response['content']
        return None
    
    def _is_indian_career_query(self, message: str) -> bool:
        """Check if query is specific to Indian job market"""
        message_lower = message.lower()
        
        indian_keywords = [
            'india', 'indian', 'naukri', 'linkedin india',
            'bangalore', 'mumbai', 'delhi', 'chennai', 'hyderabad', 'pune',
            'tcs', 'infosys', 'wipro', 'hcl', 'tech mahindra',
            'ctc', 'in-hand', 'notice period'
        ]
        
        return any(keyword in message_lower for keyword in indian_keywords)
    
    def clear_user_context(self, user_id: str):
        """Clear user context"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
            logger.info(f"Cleared context for user: {user_id}")
    
    def get_interview_tips(self, job_type: str, experience_level: str, user_id: str = None, company: str = None) -> Optional[str]:
        """Get interview tips for a specific job type"""
        prompt = f"Provide interview tips for {job_type} position at {experience_level} level"
        if company:
            prompt += f" at {company}"
        
        response = self.send_message(prompt, user_id)
        if response and 'content' in response:
            return response['content']
        return None
    
    def get_resume_suggestions(self, job_description: str, user_id: str = None, current_resume: str = None) -> Optional[str]:
        """Get resume suggestions based on job description"""
        prompt = f"Provide resume suggestions for this job description: {job_description}"
        if current_resume:
            prompt += f"\nCurrent resume: {current_resume}"
        
        response = self.send_message(prompt, user_id)
        if response and 'content' in response:
            return response['content']
        return None
    
    def get_career_advice(self, current_situation: str, goals: str, user_id: str = None) -> Optional[str]:
        """Get career development advice"""
        prompt = f"Current situation: {current_situation}\nGoals: {goals}\nProvide career advice."
        
        response = self.send_message(prompt, user_id)
        if response and 'content' in response:
            return response['content']
        return None
    
    def get_salary_guidance(self, role: str, experience: str, location: str, user_id: str = None, industry: str = None) -> Optional[str]:
        """Get salary negotiation guidance"""
        prompt = f"Provide salary guidance for {role} with {experience} experience in {location}"
        if industry:
            prompt += f" in {industry} industry"
        
        response = self.send_message(prompt, user_id)
        if response and 'content' in response:
            return response['content']
        return None
    
    def reset_session(self) -> bool:
        """Reset the chatbot session"""
        try:
            self.session_id = str(uuid.uuid4())
            self.user_contexts.clear()
            logger.info("Chatbot session reset successfully")
            return True
        except Exception as e:
            logger.error(f"Error resetting session: {e}")
            return False
    
    def get_conversation_summary(self, user_id: str) -> Optional[str]:
        """Get conversation summary for a user"""
        # This is a placeholder - in a real implementation, you would store conversation history
        return f"Conversation summary for user {user_id}"
    
    def get_session_history(self) -> Optional[list]:
        """Get chat session history"""
        # This is a placeholder - in a real implementation, you would store conversation history
        return []

# Global chatbot service instance
chatbot_service = ChatbotService()
logger.info("Chatbot service initialized successfully")