# services/deepseek_service.py
import os
import json
import re
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DeepSeekService:
    """Service for interacting with DeepSeek API to generate questions and content"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_test_questions(self, job_title: str, job_description: str, 
                              skills: str, experience_level: str, 
                              num_questions: int = 10) -> List[Dict[str, Any]]:
        """
        Generate test questions based on job requirements using DeepSeek API
        
        Args:
            job_title: Title of the position
            job_description: Detailed job description
            skills: Required skills for the position
            experience_level: Required experience level
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions with metadata
        """
        try:
            prompt = self._build_question_generation_prompt(
                job_title, job_description, skills, experience_level, num_questions
            )
            
            response = self._call_deepseek_api(prompt)
            questions = self._parse_questions_response(response)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return []
    
    def generate_interview_questions(self, job_title: str, job_description: str,
                                   skills: str, experience_level: str,
                                   interview_type: str = "Technical") -> List[Dict[str, Any]]:
        """
        Generate interview questions based on job requirements
        
        Args:
            job_title: Title of the position
            job_description: Detailed job description
            skills: Required skills for the position
            experience_level: Required experience level
            interview_type: Type of interview (Technical, Behavioral, HR)
            
        Returns:
            List of interview questions
        """
        try:
            prompt = self._build_interview_question_prompt(
                job_title, job_description, skills, experience_level, interview_type
            )
            
            response = self._call_deepseek_api(prompt)
            questions = self._parse_interview_questions_response(response)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            return []
    
    def evaluate_test_answers(self, questions: List[Dict], answers: Dict[str, str],
                            job_context: str) -> Dict[str, Any]:
        """
        Evaluate test answers using AI
        
        Args:
            questions: List of questions with correct answers
            answers: Candidate's answers
            job_context: Job description for context
            
        Returns:
            Evaluation results with scores and feedback
        """
        try:
            prompt = self._build_evaluation_prompt(questions, answers, job_context)
            
            response = self._call_deepseek_api(prompt)
            evaluation = self._parse_evaluation_response(response)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating answers: {str(e)}")
            return {"score": 0, "feedback": "Error evaluating answers"}
    
    def generate_job_description(self, job_title: str, department: str, 
                               skills: str, experience: str) -> str:
        """
        Generate a comprehensive job description
        
        Args:
            job_title: Title of the position
            department: Department name
            skills: Required skills
            experience: Experience requirements
            
        Returns:
            Generated job description
        """
        try:
            prompt = f"""
            Generate a professional job description for the following position:
            
            Job Title: {job_title}
            Department: {department}
            Required Skills: {skills}
            Experience Level: {experience}
            
            Please include:
            - Company overview (generic)
            - Position summary
            - Key responsibilities
            - Required qualifications
            - Preferred qualifications
            - Benefits and perks
            - Application instructions
            
            Format it professionally with clear sections.
            """
            
            response = self._call_deepseek_api(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating job description: {str(e)}")
            return "Error generating job description"
    
    def _call_deepseek_api(self, prompt: str, model: str = "deepseek/deepseek-chat") -> str:
        """Make API call to DeepSeek"""
        try:
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert HR and recruitment assistant."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": { "type": "json_object" }, # This is the magic line
                "temperature": 0.1, # Lower temperature = more stable JSON
                "max_tokens": 2000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                    result = response.json()
                    # Ensure you use [0] to access the first choice!
                    content = result["choices"][0]["message"]["content"]
                    return content
            else:
                    logger.error(f"DeepSeek API error: {response.status_code}")
                    raise Exception(f"API call failed: {response.status_code}")

        except Exception as e: # This was missing or misaligned!
                logger.error(f"Error in API call: {str(e)}")
                raise Exception(f"Request failed: {str(e)}")
    
    def _build_question_generation_prompt(self, job_title: str, job_description: str,
                                        skills: str, experience_level: str,
                                        num_questions: int) -> str:
        """Build prompt for question generation"""
        return f"""
        Generate {num_questions} multiple-choice questions for a technical test based on the following job requirements:
        
        Job Title: {job_title}
        Job Description: {job_description}
        Required Skills: {skills}
        Experience Level: {experience_level}
        
        Requirements:
        1. Questions should be relevant to the job requirements
        2. Include a mix of technical and conceptual questions
        3. Each question should have 4 options (A, B, C, D)
        4. Clearly indicate the correct answer
        5. Assign difficulty level (Easy, Medium, Hard)
        6. Assign points (1-3 based on difficulty)
        7. Categorize each question (e.g., Programming, Database, Algorithms, etc.)
        
        Format the response as JSON array with the following structure:
        [
            {{
                "question_text": "Question text here",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "A",
                "difficulty": "Medium",
                "points": 2,
                "category": "Programming"
            }}
        ]
        
        Ensure the JSON is valid and properly formatted.
        """
    
    def _build_interview_question_prompt(self, job_title: str, job_description: str,
                                       skills: str, experience_level: str,
                                       interview_type: str) -> str:
        """Build prompt for interview question generation"""
        return f"""
        Generate 8-10 interview questions for a {interview_type.lower()} interview based on:
        
        Job Title: {job_title}
        Job Description: {job_description}
        Required Skills: {skills}
        Experience Level: {experience_level}
        Interview Type: {interview_type}
        
        Requirements:
        1. Questions should be appropriate for {interview_type.lower()} interview
        2. Include behavioral questions if applicable
        3. Questions should assess the candidate's fit for the role
        4. Include follow-up suggestions for each question
        5. Rate each question's importance (High, Medium, Low)
        
        Format the response as JSON array:
        [
            {{
                "question_text": "Question here",
                "question_type": "Technical/Behavioral/Situational",
                "importance": "High",
                "follow_up_suggestions": "Suggested follow-up questions",
                "what_to_look_for": "What to evaluate in the answer"
            }}
        ]
        
        Ensure the JSON is valid and properly formatted.
        """
    
    def _build_evaluation_prompt(self, questions: List[Dict], answers: Dict[str, str],
                               job_context: str) -> str:
        """Build prompt for answer evaluation"""
        questions_text = json.dumps(questions, indent=2)
        answers_text = json.dumps(answers, indent=2)
        
        return f"""
        Evaluate the following test answers and provide detailed feedback:
        
        Job Context: {job_context}
        
        Questions:
        {questions_text}
        
        Candidate Answers:
        {answers_text}
        
        Please provide:
        1. Total score (out of maximum possible points)
        2. Percentage score
        3. Question-by-question evaluation
        4. Overall feedback
        5. Strengths demonstrated
        6. Areas for improvement
        7. Recommendation (Strong Hire, Hire, Consider, Reject)
        
        Format the response as JSON:
        {{
            "total_score": 25,
            "max_score": 30,
            "percentage": 83.3,
            "question_evaluations": [
                {{
                    "question_id": "q1",
                    "correct": true,
                    "points_earned": 2,
                    "feedback": "Good understanding of concepts"
                }}
            ],
            "overall_feedback": "Detailed feedback here",
            "strengths": ["Technical knowledge", "Problem solving"],
            "improvements": ["Need more practice in X"],
            "recommendation": "Hire"
        }}
        
        Ensure the JSON is valid and properly formatted.
        """
    
    def _parse_questions_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the questions response from DeepSeek"""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                questions = json.loads(json_str)
                return questions
            else:
                logger.error("Could not find valid JSON in response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return []
    
    def _parse_interview_questions_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the interview questions response"""
        return self._parse_questions_response(response)
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse the evaluation response"""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                evaluation = json.loads(json_str)
                return evaluation
            else:
                logger.error("Could not find valid JSON in evaluation response")
                return {"score": 0, "feedback": "Error parsing evaluation"}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in evaluation: {str(e)}")
            return {"score": 0, "feedback": "Error parsing evaluation"}

# Singleton instance
deepseek_service = DeepSeekService()