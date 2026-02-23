# services/gemini_agent_service.py
import os
import sys
import logging
from typing import Dict, Any, Optional, List

# Add chatbot directory to path
chatbot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'chatbot'))
if chatbot_path not in sys.path:
    sys.path.append(chatbot_path)

logger = logging.getLogger(__name__)

class GeminiAgentService:
    """Google Gemini ADK Agent Service"""
    
    def __init__(self):
        self.initialized = False
        self.agent = None
        self.sessions = {}
        
        try:
            # Import and initialize ADK agent
            logger.debug(f"Attempting to import from chatbot path: {chatbot_path}")
            # After adding chatbot_path to sys.path, we can import directly
            from agents.agent import root_agent
            self.agent = root_agent
            self.initialized = True
            logger.info(f"[OK] Gemini ADK Agent initialized: {self.agent.name}")
            logger.info(f"   Model: {self.agent.model}")
            logger.info(f"   Sub-agents: {[a.name for a in self.agent.sub_agents] if hasattr(self.agent, 'sub_agents') else 'None'}")
        except ImportError as e:
            logger.error(f"[FAIL] Failed to import Gemini Agent: {str(e)}")
            logger.error(f"   Chatbot path: {chatbot_path}")
            logger.error(f"   Path exists: {os.path.exists(chatbot_path)}")
            if os.path.exists(chatbot_path):
                logger.error(f"   Contents: {os.listdir(chatbot_path)}")
            self.initialized = False
        except Exception as e:
            logger.error(f"[FAIL] Failed to initialize Gemini Agent: {str(e)}")
            self.initialized = False
    
    def get_response(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> Optional[str]:
        """Get response from Gemini ADK agent"""
        if not self.initialized:
            return None
        
        try:
            # For now, return a mock response since the ADK integration needs more work
            # This is a placeholder that will be enhanced once the ADK API is fully understood
            logger.info("[INFO] Using placeholder response for Gemini agent")
            
            # Check if it's an Indian career query
            message_lower = message.lower()
            indian_keywords = ['india', 'indian', 'bangalore', 'mumbai', 'tcs', 'infosys', 'ctc']
            is_indian = any(keyword in message_lower for keyword in indian_keywords)
            
            if is_indian:
                return """Based on your query about the Indian job market, here's some guidance:

For Indian job seekers, especially in tech hubs like Bangalore and Mumbai:
- Focus on skills relevant to Indian IT companies (TCS, Infosys, Wipro, etc.)
- Understand CTC (Cost to Company) structure including Basic, HRA, Special Allowance
- Be prepared for technical interviews followed by HR discussions
- Notice period negotiation is common in Indian companies
- Consider both MNCs and growing startups for better opportunities

Would you like more specific advice on any aspect?"""
            else:
                return """I'm here to help with your career journey! I can assist with:

- Job recommendations based on your skills and experience
- Resume optimization tips
- Interview preparation guidance
- Career development advice
- Salary negotiation strategies

What specific area would you like help with?"""
            
        except Exception as e:
            logger.error(f"[FAIL] Gemini Agent error: {str(e)}")
            return None
    
    def get_career_advice_indian(self, user_profile: Dict[str, Any]) -> Optional[str]:
        """Get Indian-specific career advice using Gemini's local knowledge"""
        prompt = f"""As an Indian career expert, provide detailed advice for:

User Profile:
- Skills: {user_profile.get('skills', 'Not specified')}
- Experience: {user_profile.get('experience', 'Not specified')}
- Education: {user_profile.get('education', 'Not specified')}
- Location: {user_profile.get('location', 'India')}
- Preferences: {user_profile.get('preferences', 'Not specified')}

Please provide:
1. Indian job market analysis for their skills
2. Company recommendations (Indian MNCs, startups, international)
3. CTC salary expectations with city-wise breakdown
4. Notice period negotiation strategies
5. Indian-specific career growth paths
6. Recommended Indian job portals (Naukri, LinkedIn India, etc.)"""
        
        return self.get_response(prompt, context=user_profile)
    
    def get_resume_review_indian(self, resume_text: str) -> Optional[str]:
        """Review resume for Indian job market standards"""
        prompt = f"""Review this resume for Indian job market:

{resume_text[:3000]}  # Truncate for token limits

Provide:
1. ATS optimization for Indian companies (TCS, Infosys, etc.)
2. Indian resume format corrections
3. Skills to highlight for Indian market
4. Common mistakes in Indian resumes
5. Indian-specific keywords to add
6. Template suggestions for Indian recruiters"""
        
        return self.get_response(prompt)
    
    def get_interview_prep_indian(self, company: str, role: str) -> Optional[str]:
        """Indian company-specific interview preparation"""
        prompt = f"""Provide interview preparation for:

Company: {company} (Indian context)
Role: {role}

Include:
1. Company-specific interview rounds (e.g., Infosys: Aptitude, Technical, HR)
2. Common technical questions for this role in India
3. Cultural fit questions for Indian work culture
4. Salary negotiation tips for Indian companies
5. What Indian recruiters look for
6. Follow-up etiquette in Indian companies"""
        
        return self.get_response(prompt)
    
    def get_salary_benchmarks_indian(self, role: str, experience: str, location: str) -> Optional[str]:
        """Get Indian salary benchmarks"""
        prompt = f"""Provide detailed salary benchmarks for India:

Role: {role}
Experience: {experience}
Location: {location}

Include:
1. CTC breakdown (Basic, HRA, Allowances, Bonus)
2. In-hand salary calculation after deductions
3. City-wise comparison
4. Industry-wise variations (IT vs Manufacturing vs Banking)
5. Benefits typical in Indian companies (PF, Gratuity, Insurance)
6. Negotiation range for this profile"""
        
        return self.get_response(prompt)

# Global instance
gemini_agent_service = GeminiAgentService()