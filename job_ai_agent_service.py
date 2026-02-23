import os
import json
import requests
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class JobAIAgentService:
    """AI Agent service for job and career assistance using OpenAI API"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.deepseek_url = "https://api.deepseek.com/v3.1"
        self.model = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
        self.fallback_model = 'deepseek-chat'
        self.conversation_history = {}

    # Add to JobAIAgentService class methods
    def get_ai_response(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced to return metadata"""
        response_text = self._get_ai_response_text(message, user_id, context)
        
        return {
            "content": response_text,
            "source": "openai",  # or "deepseek"
            "model": self.model if response_text else None,
            "timestamp": datetime.now().isoformat()
        }

    # def _get_ai_response_text(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> Optional[str]:
    #     """Original method renamed"""
    #     # ... keep existing implementation ...
        
    def _get_headers(self, use_deepseek=False):
        """Get appropriate headers for API calls"""
        if use_deepseek:
            return {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
        return {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build system prompt for job/career assistance"""
        base_prompt = """You are JobSphere AI, a professional career assistant and job search expert. 
        Your role is to help job seekers with personalized advice, recommendations, and guidance.
        
        Key capabilities:
        - Provide job recommendations based on skills, experience, and preferences
        - Offer interview tips and preparation advice
        - Help with resume optimization and cover letter writing
        - Give career guidance and skill development suggestions
        - Provide salary negotiation tips and market insights
        - Assist with networking strategies and job search techniques
        
        Guidelines:
        - Be professional, encouraging, and supportive
        - Provide actionable and specific advice
        - Ask clarifying questions when needed to give better recommendations
        - Keep responses concise but comprehensive
        - Use markdown formatting for better readability
        - Always consider the user's context and background"""
        
        if context:
            context_str = f"\n\nUser Context:\n"
            if context.get('skills'):
                context_str += f"- Skills: {context['skills']}\n"
            if context.get('experience'):
                context_str += f"- Experience: {context['experience']}\n"
            if context.get('education'):
                context_str += f"- Education: {context['education']}\n"
            if context.get('location'):
                context_str += f"- Location: {context['location']}\n"
            if context.get('preferences'):
                context_str += f"- Preferences: {context['preferences']}\n"
            base_prompt += context_str
        
        return base_prompt
    
    def _call_ai_api(self, messages: List[Dict], use_deepseek) -> Optional[str]:
        """Make API call to AI service"""
        try:
            url = f"{self.deepseek_url}/chat/completions" if use_deepseek else f"{self.base_url}/chat/completions"
            headers = self._get_headers(use_deepseek)
            model = self.fallback_model if use_deepseek else self.model
            
            logger.info(f"[AI_AGENT_DEBUG] API URL: {url}")
            logger.info(f"[AI_AGENT_DEBUG] Model: {model}")
            logger.info(f"[AI_AGENT_DEBUG] Using DeepSeek: {use_deepseek}")
            logger.info(f"[AI_AGENT_DEBUG] Messages count: {len(messages)}")
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1500,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            logger.info(f"[AI_AGENT_DEBUG] Sending request to API...")
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            logger.info(f"[AI_AGENT_DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"[AI_AGENT_DEBUG] Successfully parsed response, length: {len(content)}")
                return content
            else:
                error_msg = f"AI API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                logger.error(f"[AI_AGENT_DEBUG] Request failed: {error_msg}")
                return None
                
        except Exception as e:
            error_msg = f"Error calling AI API: {str(e)}"
            logger.error(error_msg)
            logger.error(f"[AI_AGENT_DEBUG] Exception occurred: {error_msg}")
            return None
    
    def _get_ai_response_text(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> Optional[str]:
        """Get AI response for user message"""
        try:
            logger.info(f"[AI_AGENT_DEBUG] Getting AI response for user_id: {user_id}")
            logger.info(f"[AI_AGENT_DEBUG] OpenAI API key configured: {'Yes' if self.openai_api_key and self.openai_api_key != 'your_openai_api_key_here' else 'No'}")
            logger.info(f"[AI_AGENT_DEBUG] DeepSeek API key configured: {'Yes' if self.deepseek_api_key and self.deepseek_api_key and self.deepseek_api_key != 'your_deepseek_api_key_here' else 'No'}")
            logger.info(f"[AI_AGENT_DEBUG] Message: {message[:100]}...")
            
            # Initialize conversation history for new users
            if user_id and user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
                logger.info(f"[AI_AGENT_DEBUG] Initialized conversation history for user: {user_id}")
            
            # Build messages array
            messages = [
                {"role": "system", "content": self._build_system_prompt(context)}
            ]
            
            # Add conversation history (last 5 messages for context)
            if user_id and user_id in self.conversation_history:
                messages.extend(self.conversation_history[user_id][-5:])
                logger.info(f"[AI_AGENT_DEBUG] Added {len(self.conversation_history[user_id][-5:])} messages from history")
            
            # Add current message
            messages.append({"role": "user", "content": message})
            logger.info(f"[AI_AGENT_DEBUG] Total messages for API: {len(messages)}")
            
            # Try OpenAI first
            logger.info(f"[AI_AGENT_DEBUG] Calling OpenAI API...")
            response = self._call_ai_api(messages, use_deepseek=False)
            logger.info(f"[AI_AGENT_DEBUG] OpenAI response received: {'Yes' if response else 'No'}")
            
            # If OpenAI fails, try DeepSeek as fallback
            if not response:
                logger.info(f"[AI_AGENT_DEBUG] OpenAI failed, trying DeepSeek fallback...")
                response = self._call_ai_api(messages, use_deepseek=True)
                logger.info(f"[AI_AGENT_DEBUG] DeepSeek response received: {'Yes' if response else 'No'}")
            
            if response:
                logger.info(f"[AI_AGENT_DEBUG] Success! Returning response of length: {len(response)}")
                # Update conversation history
                if user_id:
                    self.conversation_history[user_id].append({"role": "user", "content": message})
                    self.conversation_history[user_id].append({"role": "assistant", "content": response})
                    
                    # Keep only last 10 messages
                    if len(self.conversation_history[user_id]) > 10:
                        self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
                
                return response
            else:
                logger.error("[AI_AGENT_DEBUG] Failed to get response from both AI APIs")
                return None
                
        except Exception as e:
            logger.error(f"[AI_AGENT_DEBUG] Error getting AI response: {str(e)}")
            return None
    
    def get_job_recommendations(self, user_profile: Dict[str, Any]) -> Optional[str]:
        """Get personalized job recommendations"""
        prompt = f"""
        Based on the following user profile, provide personalized job recommendations:
        
        User Profile:
        - Skills: {user_profile.get('skills', 'Not specified')}
        - Experience: {user_profile.get('experience', 'Not specified')}
        - Education: {user_profile.get('education', 'Not specified')}
        - Location: {user_profile.get('location', 'Not specified')}
        - Job Preferences: {user_profile.get('preferences', 'Not specified')}
        
        Please provide:
        1. Top 5 recommended job roles with brief descriptions
        2. Skills to highlight for each role
        3. Potential companies or industries to target
        4. Salary expectations based on market data
        5. Next steps for job search
        """
        
        return self.get_ai_response(prompt, context=user_profile)
    
    def get_interview_tips(self, job_type: str, experience_level: str, company: str = None) -> Optional[str]:
        """Get interview preparation tips"""
        prompt = f"""
        Provide comprehensive interview preparation tips for:
        
        Position: {job_type}
        Experience Level: {experience_level}
        Company: {company if company else 'Not specified'}
        
        Please include:
        1. Common interview questions for this role
        2. Technical topics to review
        3. Behavioral questions using STAR method examples
        4. Questions to ask the interviewer
        5. Preparation checklist for the week before
        6. Virtual vs in-person interview tips
        """
        
        context = {
            'job_type': job_type,
            'experience': experience_level,
            'company': company
        }
        
        return self.get_ai_response(prompt, context=context)
    
    def get_resume_suggestions(self, job_description: str, current_resume: str = None) -> Optional[str]:
        """Get resume optimization suggestions"""
        prompt = f"""
        Provide resume optimization suggestions based on:
        
        Job Description:
        {job_description}
        
        Current Resume: {current_resume if current_resume else 'Not provided'}
        
        Please provide:
        1. Key skills and keywords to include
        2. Experience formatting recommendations
        3. Achievement quantification suggestions
        4. Structure and layout improvements
        5. ATS optimization tips
        6. Specific phrases and power words to use
        """
        
        return self.get_ai_response(prompt)
    
    def get_career_advice(self, current_situation: str, goals: str) -> Optional[str]:
        """Get career development advice"""
        prompt = f"""
        Provide career development advice for:
        
        Current Situation: {current_situation}
        Career Goals: {goals}
        
        Please provide:
        1. Skill development roadmap
        2. Certification or education recommendations
        3. Networking strategies
        4. Industry trends to watch
        5. Potential career paths
        6. Timeline and milestones
        """
        
        return self.get_ai_response(prompt)
    
    def get_salary_guidance(self, role: str, experience: str, location: str, industry: str = None) -> Optional[str]:
        """Get salary negotiation guidance"""
        prompt = f"""
        Provide salary negotiation guidance for:
        
        Role: {role}
        Experience Level: {experience}
        Location: {location}
        Industry: {industry if industry else 'Not specified'}
        
        Please provide:
        1. Market salary range for this role
        2. Factors that affect compensation
        3. Negotiation strategies and talking points
        4. Benefits and perks to consider
        5. When and how to discuss salary
        6. Red flags to watch for
        """
        
        return self.get_ai_response(prompt)
    
    def clear_conversation_history(self, user_id: str):
        """Clear conversation history for a user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
    
    def get_conversation_summary(self, user_id: str) -> Optional[str]:
        """Get a summary of the conversation history"""
        if user_id not in self.conversation_history:
            return None
        
        history = self.conversation_history[user_id]
        if not history:
            return None
        
        # Create a summary of the conversation
        summary_prompt = "Summarize the following conversation between a job seeker and career assistant:\n\n"
        for msg in history[-10:]:  # Last 10 messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            summary_prompt += f"{role}: {msg['content']}\n\n"
        
        summary_prompt += "\nProvide a concise summary of the key topics discussed and advice given."
        
        return self.get_ai_response(summary_prompt)

# Global instance
job_ai_agent_service = JobAIAgentService()