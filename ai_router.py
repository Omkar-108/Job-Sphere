# services/ai_router.py
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AIProvider(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    MOCK = "mock"

class AIRouter:
    """Intelligent router to best AI provider"""
    
    def __init__(self):
        self.providers = {}
        self.performance_stats = {}
        
    def register_provider(self, name: str, provider, priority: int = 0):
        """Register an AI provider"""
        self.providers[name] = {
            'instance': provider,
            'priority': priority,
            'available': True
        }
    
    def get_best_response(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get response from best available provider"""
        
        # Analyze query type
        query_type = self._analyze_query_type(message)
        
        # Select provider based on query type
        if query_type == "indian_career":
            preferred_providers = ['gemini', 'openai', 'deepseek']
        elif query_type == "technical":
            preferred_providers = ['openai', 'deepseek', 'gemini']
        elif query_type == "general":
            preferred_providers = ['openai', 'gemini', 'deepseek']
        else:
            preferred_providers = ['openai', 'gemini', 'deepseek']
        
        # Try providers in order
        for provider_name in preferred_providers:
            if provider_name in self.providers and self.providers[provider_name]['available']:
                try:
                    provider = self.providers[provider_name]['instance']
                    response = provider.get_response(message, context=context)
                    
                    if response and response.get('content'):
                        return {
                            **response,
                            "provider": provider_name,
                            "query_type": query_type
                        }
                except Exception as e:
                    logger.error(f"Provider {provider_name} failed: {e}")
                    self.providers[provider_name]['available'] = False
        
        # All providers failed
        return {
            "content": "I apologize, but I'm having trouble connecting to my AI services. Please try again in a moment.",
            "provider": "error",
            "query_type": query_type
        }
    
    def _analyze_query_type(self, message: str) -> str:
        """Analyze what type of query this is"""
        message_lower = message.lower()
        
        # Indian career queries
        indian_indicators = ['india', 'indian', 'naukri', 'ctc', 'notice period', 'bangalore', 'mumbai']
        
        # Technical queries
        technical_indicators = ['code', 'programming', 'algorithm', 'bug', 'error', 'debug', 'python', 'javascript']
        
        # Resume/interview queries
        career_indicators = ['resume', 'cv', 'interview', 'salary', 'job', 'career', 'hire']
        
        if any(ind in message_lower for ind in indian_indicators):
            return "indian_career"
        elif any(tech in message_lower for tech in technical_indicators):
            return "technical"
        elif any(career in message_lower for career in career_indicators):
            return "career"
        else:
            return "general"

# Global router instance
ai_router = AIRouter()