# services/interview_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId

from database.models import Interview, InterviewFeedback, Application, Job, HR
from database.repository import DatabaseRepository
from services.deepseek_service import deepseek_service

logger = logging.getLogger(__name__)

class InterviewService:
    """Service for managing interviews and scheduling"""
    
    def __init__(self):
        self.db = DatabaseRepository()
    
    def schedule_interview(self, application_id: str, job_id: str, candidate_id: str,
                          hr_id: str, interview_type: str, scheduled_datetime: datetime,
                          duration_minutes: int = 60, meeting_link: str = None,
                          location: str = None) -> str:
        """
        Schedule a new interview
        
        Args:
            application_id: ID of the application
            job_id: ID of the job
            candidate_id: ID of the candidate
            hr_id: ID of the HR conducting the interview
            interview_type: Type of interview (Phone, Video, In-person, Technical)
            scheduled_datetime: When the interview is scheduled
            duration_minutes: Duration of the interview
            meeting_link: Meeting link for virtual interviews
            location: Location for in-person interviews
            
        Returns:
            ID of the created interview
        """
        try:
            interview = Interview(
                application_id=application_id,
                job_id=job_id,
                candidate_id=candidate_id,
                hr_id=hr_id,
                interview_type=interview_type,
                scheduled_datetime=scheduled_datetime,
                duration_minutes=duration_minutes,
                meeting_link=meeting_link,
                location=location,
                status="Scheduled"
            )
            
            interview_id = self.db.insert_one("interviews", interview.to_dict())
            
            # Update application status
            self.db.update_one(
                "applications",
                {"_id": ObjectId(application_id)},
                {"status": "Interview Scheduled", "updated_at": datetime.now()}
            )
            
            # Update candidate pipeline
            self._update_candidate_pipeline(application_id, "Interview Scheduled")
            
            logger.info(f"Scheduled interview {interview_id} for candidate {candidate_id}")
            return str(interview_id)
            
        except Exception as e:
            logger.error(f"Error scheduling interview: {str(e)}")
            raise
    
    def generate_interview_questions(self, job_id: str, interview_type: str = "Technical") -> List[Dict[str, Any]]:
        """
        Generate interview questions for a job using DeepSeek API
        
        Args:
            job_id: ID of the job
            interview_type: Type of interview
            
        Returns:
            List of generated interview questions
        """
        try:
            # Get job details
            job_data = self.db.find_one("jobs", {"_id": ObjectId(job_id)})
            if not job_data:
                logger.error(f"Job {job_id} not found")
                return []
            
            job = Job.from_dict(job_data)
            
            # Generate questions using DeepSeek
            questions = deepseek_service.generate_interview_questions(
                job.title, job.description, job.skills, job.experience, interview_type
            )
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            return []
    
    def get_interview_details(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed interview information
        
        Args:
            interview_id: ID of the interview
            
        Returns:
            Interview details or None if not found
        """
        try:
            # Get interview
            interview_data = self.db.find_one("interviews", {"_id": ObjectId(interview_id)})
            if not interview_data:
                return None
            
            # Get related data
            application_data = self.db.find_one("applications", {"_id": ObjectId(interview_data["application_id"])})
            job_data = self.db.find_one("jobs", {"_id": ObjectId(interview_data["job_id"])})
            hr_data = self.db.find_one("hrs", {"_id": ObjectId(interview_data["hr_id"])})
            
            # Get feedback if exists
            feedback_data = self.db.find_one("interview_feedback", {"interview_id": interview_id})
            
            interview_data["_id"] = str(interview_data["_id"])
            interview_data["application"] = application_data
            interview_data["job"] = job_data
            interview_data["hr"] = hr_data
            interview_data["feedback"] = feedback_data
            
            return interview_data
            
        except Exception as e:
            logger.error(f"Error getting interview details: {str(e)}")
            return None
    
    def update_interview_status(self, interview_id: str, status: str, notes: str = None) -> bool:
        """
        Update interview status
        
        Args:
            interview_id: ID of the interview
            status: New status (Scheduled, In Progress, Completed, Cancelled, No Show)
            notes: Optional notes about the status change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now()
            }
            
            if notes:
                update_data["notes"] = notes
            
            self.db.update_one(
                "interviews",
                {"_id": ObjectId(interview_id)},
                update_data
            )
            
            # Update application status if interview is completed
            if status == "Completed":
                interview_data = self.db.find_one("interviews", {"_id": ObjectId(interview_id)})
                if interview_data:
                    self.db.update_one(
                        "applications",
                        {"_id": ObjectId(interview_data["application_id"])},
                        {"status": "Interview Completed", "updated_at": datetime.now()}
                    )
            
            logger.info(f"Updated interview {interview_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating interview status: {str(e)}")
            return False
    
    def submit_interview_feedback(self, interview_id: str, interviewer_id: str,
                                technical_skills: int, communication_skills: int,
                                problem_solving: int, cultural_fit: int,
                                strengths: List[str], weaknesses: List[str],
                                comments: str, recommendation: str) -> str:
        """
        Submit feedback for an interview
        
        Args:
            interview_id: ID of the interview
            interviewer_id: ID of the interviewer
            technical_skills: Rating 1-5
            communication_skills: Rating 1-5
            problem_solving: Rating 1-5
            cultural_fit: Rating 1-5
            strengths: List of candidate strengths
            weaknesses: List of candidate weaknesses
            comments: Additional comments
            recommendation: Hire, Reject, Consider
            
        Returns:
            ID of the feedback record
        """
        try:
            overall_rating = (technical_skills + communication_skills + 
                            problem_solving + cultural_fit) // 4
            
            feedback = InterviewFeedback(
                interview_id=interview_id,
                interviewer_id=interviewer_id,
                technical_skills=technical_skills,
                communication_skills=communication_skills,
                problem_solving=problem_solving,
                cultural_fit=cultural_fit,
                overall_rating=overall_rating,
                strengths=strengths,
                weaknesses=weaknesses,
                comments=comments,
                recommendation=recommendation
            )
            
            feedback_id = self.db.insert_one("interview_feedback", feedback.to_dict())
            
            # Update interview with feedback summary
            self.db.update_one(
                "interviews",
                {"_id": ObjectId(interview_id)},
                {
                    "feedback": comments,
                    "rating": overall_rating,
                    "updated_at": datetime.now()
                }
            )
            
            # Update application status based on recommendation
            self._update_application_from_feedback(interview_id, recommendation)
            
            logger.info(f"Submitted feedback for interview {interview_id}")
            return str(feedback_id)
            
        except Exception as e:
            logger.error(f"Error submitting interview feedback: {str(e)}")
            raise
    
    def _update_application_from_feedback(self, interview_id: str, recommendation: str):
        """Update application status based on interview feedback"""
        try:
            interview_data = self.db.find_one("interviews", {"_id": ObjectId(interview_id)})
            if not interview_data:
                return
            
            application_id = interview_data["application_id"]
            
            # Map recommendation to application status
            status_mapping = {
                "Hire": "Interview Passed",
                "Reject": "Interview Failed",
                "Consider": "Under Review"
            }
            
            new_status = status_mapping.get(recommendation, "Under Review")
            
            self.db.update_one(
                "applications",
                {"_id": ObjectId(application_id)},
                {"status": new_status, "updated_at": datetime.now()}
            )
            
            # Update candidate pipeline
            pipeline_stage = "Interview Passed" if recommendation == "Hire" else "Interview Failed"
            self._update_candidate_pipeline(application_id, pipeline_stage)
            
        except Exception as e:
            logger.error(f"Error updating application from feedback: {str(e)}")
    
    def get_interviews_for_hr(self, hr_id: str, status: str = None) -> List[Dict[str, Any]]:
        """
        Get interviews scheduled for a specific HR
        
        Args:
            hr_id: ID of the HR
            status: Optional status filter
            
        Returns:
            List of interviews
        """
        try:
            query = {"hr_id": hr_id}
            if status:
                query["status"] = status
            
            interviews_cursor = self.db.find_many(
                "interviews",
                query,
                sort=[("scheduled_datetime", 1)]
            )
            
            interviews = []
            for interview in interviews_cursor:
                # Get related data
                application_data = self.db.find_one("applications", {"_id": ObjectId(interview["application_id"])})
                job_data = self.db.find_one("jobs", {"_id": ObjectId(interview["job_id"])})
                
                interview["_id"] = str(interview["_id"])
                interview["application"] = application_data
                interview["job"] = job_data
                
                interviews.append(interview)
            
            return interviews
            
        except Exception as e:
            logger.error(f"Error getting interviews for HR {hr_id}: {str(e)}")
            return []
    
    def get_candidate_interviews(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get all interviews for a candidate
        
        Args:
            candidate_id: ID of the candidate
            
        Returns:
            List of interviews
        """
        try:
            interviews_cursor = self.db.find_many(
                "interviews",
                {"candidate_id": candidate_id},
                sort=[("scheduled_datetime", -1)]
            )
            
            interviews = []
            for interview in interviews_cursor:
                # Get related data
                application_data = self.db.find_one("applications", {"_id": ObjectId(interview["application_id"])})
                job_data = self.db.find_one("jobs", {"_id": ObjectId(interview["job_id"])})
                hr_data = self.db.find_one("hrs", {"_id": ObjectId(interview["hr_id"])})
                
                interview["_id"] = str(interview["_id"])
                interview["application"] = application_data
                interview["job"] = job_data
                interview["hr"] = hr_data
                
                interviews.append(interview)
            
            return interviews
            
        except Exception as e:
            logger.error(f"Error getting candidate interviews: {str(e)}")
            return []
    
    def get_upcoming_interviews(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get upcoming interviews within specified days
        
        Args:
            days_ahead: Number of days ahead to look
            
        Returns:
            List of upcoming interviews
        """
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)
            
            interviews_cursor = self.db.find_many(
                "interviews",
                {
                    "scheduled_datetime": {"$gte": start_date, "$lte": end_date},
                    "status": {"$in": ["Scheduled", "In Progress"]}
                },
                sort=[("scheduled_datetime", 1)]
            )
            
            interviews = []
            for interview in interviews_cursor:
                # Get related data
                application_data = self.db.find_one("applications", {"_id": ObjectId(interview["application_id"])})
                job_data = self.db.find_one("jobs", {"_id": ObjectId(interview["job_id"])})
                hr_data = self.db.find_one("hrs", {"_id": ObjectId(interview["hr_id"])})
                
                interview["_id"] = str(interview["_id"])
                interview["application"] = application_data
                interview["job"] = job_data
                interview["hr"] = hr_data
                
                interviews.append(interview)
            
            return interviews
            
        except Exception as e:
            logger.error(f"Error getting upcoming interviews: {str(e)}")
            return []
    
    def check_interview_conflicts(self, hr_id: str, scheduled_datetime: datetime, 
                                duration_minutes: int) -> bool:
        """
        Check if an interview conflicts with existing interviews for an HR
        
        Args:
            hr_id: ID of the HR
            scheduled_datetime: Proposed interview time
            duration_minutes: Duration of the interview
            
        Returns:
            True if there's a conflict, False otherwise
        """
        try:
            start_time = scheduled_datetime
            end_time = scheduled_datetime + timedelta(minutes=duration_minutes)
            
            # Find overlapping interviews
            conflicting_interviews = self.db.find_many(
                "interviews",
                {
                    "hr_id": hr_id,
                    "status": {"$in": ["Scheduled", "In Progress"]},
                    "scheduled_datetime": {
                        "$lt": end_time,
                        "$gte": start_time - timedelta(minutes=duration_minutes)
                    }
                }
            )
            
            return len(list(conflicting_interviews)) > 0
            
        except Exception as e:
            logger.error(f"Error checking interview conflicts: {str(e)}")
            return False
    
    def reschedule_interview(self, interview_id: str, new_datetime: datetime) -> bool:
        """
        Reschedule an interview to a new time
        
        Args:
            interview_id: ID of the interview
            new_datetime: New scheduled datetime
            
        Returns:
            True if successful, False otherwise
        """
        try:
            interview_data = self.db.find_one("interviews", {"_id": ObjectId(interview_id)})
            if not interview_data:
                logger.error(f"Interview {interview_id} not found")
                return False
            
            # Check for conflicts
            has_conflict = self.check_interview_conflicts(
                interview_data["hr_id"], 
                new_datetime, 
                interview_data["duration_minutes"]
            )
            
            if has_conflict:
                logger.warning(f"Conflict detected for rescheduled interview {interview_id}")
                return False
            
            # Update interview time
            self.db.update_one(
                "interviews",
                {"_id": ObjectId(interview_id)},
                {
                    "scheduled_datetime": new_datetime,
                    "updated_at": datetime.now()
                }
            )
            
            logger.info(f"Rescheduled interview {interview_id} to {new_datetime}")
            return True
            
        except Exception as e:
            logger.error(f"Error rescheduling interview: {str(e)}")
            return False
    
    def _update_candidate_pipeline(self, application_id: str, stage: str):
        """Update candidate pipeline stage"""
        try:
            # Find existing pipeline record
            pipeline_data = self.db.find_one("candidate_pipeline", {"application_id": application_id})
            
            if pipeline_data:
                # Update existing pipeline
                stage_history = pipeline_data.get("stage_history", [])
                stage_history.append({
                    "stage": stage,
                    "timestamp": datetime.now(),
                    "notes": f"Automated update: {stage}"
                })
                
                self.db.update_one(
                    "candidate_pipeline",
                    {"application_id": application_id},
                    {
                        "current_stage": stage,
                        "stage_history": stage_history,
                        "updated_at": datetime.now()
                    }
                )
            else:
                # Create new pipeline record
                from database.models import CandidatePipeline
                pipeline = CandidatePipeline(
                    application_id=application_id,
                    job_id="",  # Will be filled from application
                    candidate_id="",  # Will be filled from application
                    current_stage=stage,
                    stage_history=[{
                        "stage": stage,
                        "timestamp": datetime.now(),
                        "notes": f"Initial stage: {stage}"
                    }]
                )
                
                # Get application details to fill missing fields
                application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
                if application_data:
                    pipeline.job_id = application_data.get("job_id", "")
                    pipeline.candidate_id = application_data.get("user_id", "")
                
                self.db.insert_one("candidate_pipeline", pipeline.to_dict())
                
        except Exception as e:
            logger.error(f"Error updating candidate pipeline: {str(e)}")

# Singleton instance
interview_service = InterviewService()