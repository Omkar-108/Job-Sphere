# services/workflow_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from enum import Enum

from database.models import Application, Job, Test, Interview, JobOffer, CandidatePipeline, ScheduleEvent
from database.repository import DatabaseRepository
from services.test_service import test_service
from services.interview_service import interview_service
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

class WorkflowStage(Enum):
    APPLIED = "Applied"
    SCREENING = "Screening"
    TEST = "Test"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    HIRED = "Hired"
    REJECTED = "Rejected"

class WorkflowService:
    """Service for managing automated hiring workflows"""
    
    def __init__(self):
        self.db = DatabaseRepository()
        self.stage_transitions = {
            WorkflowStage.APPLIED: [WorkflowStage.SCREENING, WorkflowStage.REJECTED],
            WorkflowStage.SCREENING: [WorkflowStage.TEST, WorkflowStage.INTERVIEW, WorkflowStage.REJECTED],
            WorkflowStage.TEST: [WorkflowStage.INTERVIEW, WorkflowStage.REJECTED],
            WorkflowStage.INTERVIEW: [WorkflowStage.OFFER, WorkflowStage.REJECTED],
            WorkflowStage.OFFER: [WorkflowStage.HIRED, WorkflowStage.REJECTED],
            WorkflowStage.HIRED: [],
            WorkflowStage.REJECTED: []
        }
    
    def initiate_hiring_workflow(self, application_id: str) -> bool:
        """
        Initiate the hiring workflow for a new application
        
        Args:
            application_id: ID of the application
            
        Returns:
            True if workflow initiated successfully
        """
        try:
            # Get application details
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                logger.error(f"Application {application_id} not found")
                return False
            
            # Create candidate pipeline
            pipeline = CandidatePipeline(
                application_id=application_id,
                job_id=application_data["job_id"],
                candidate_id=application_data["user_id"],
                current_stage=WorkflowStage.APPLIED.value,
                stage_history=[{
                    "stage": WorkflowStage.APPLIED.value,
                    "timestamp": datetime.now(),
                    "notes": "Application received"
                }],
                next_action="Initial screening",
                next_action_date=datetime.now() + timedelta(days=1)
            )
            
            self.db.insert_one("candidate_pipeline", pipeline.to_dict())
            
            # Schedule initial screening
            self._schedule_screening(application_id)
            
            # Send confirmation email
            notification_service.send_application_confirmation(application_data)
            
            logger.info(f"Initiated hiring workflow for application {application_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initiating hiring workflow: {str(e)}")
            return False
    
    def advance_candidate_stage(self, application_id: str, new_stage: str, 
                              notes: str = "", auto_schedule: bool = True) -> bool:
        """
        Advance candidate to the next stage in the hiring process
        
        Args:
            application_id: ID of the application
            new_stage: New stage to advance to
            notes: Notes about the stage change
            auto_schedule: Whether to automatically schedule next steps
            
        Returns:
            True if stage advanced successfully
        """
        try:
            # Get current pipeline
            pipeline_data = self.db.find_one("candidate_pipeline", {"application_id": application_id})
            if not pipeline_data:
                logger.error(f"Pipeline not found for application {application_id}")
                return False
            
            current_stage = WorkflowStage(pipeline_data["current_stage"])
            target_stage = WorkflowStage(new_stage)
            
            # Validate transition
            if target_stage not in self.stage_transitions.get(current_stage, []):
                logger.error(f"Invalid transition from {current_stage.value} to {target_stage.value}")
                return False
            
            # Update pipeline
            stage_history = pipeline_data.get("stage_history", [])
            stage_history.append({
                "stage": target_stage.value,
                "timestamp": datetime.now(),
                "notes": notes or f"Advanced from {current_stage.value} to {target_stage.value}"
            })
            
            # Determine next action
            next_action, next_action_date = self._get_next_action(target_stage)
            
            self.db.update_one(
                "candidate_pipeline",
                {"application_id": application_id},
                {
                    "current_stage": target_stage.value,
                    "stage_history": stage_history,
                    "next_action": next_action,
                    "next_action_date": next_action_date,
                    "updated_at": datetime.now()
                }
            )
            
            # Update application status
            self.db.update_one(
                "applications",
                {"_id": ObjectId(application_id)},
                {"status": target_stage.value, "updated_at": datetime.now()}
            )
            
            # Auto-schedule next steps if enabled
            if auto_schedule:
                self._schedule_next_steps(application_id, target_stage)
            
            # Send notification
            self._send_stage_notification(application_id, target_stage)
            
            logger.info(f"Advanced application {application_id} to {target_stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error advancing candidate stage: {str(e)}")
            return False
    
    def _schedule_next_steps(self, application_id: str, stage: WorkflowStage):
        """Schedule next steps based on current stage"""
        try:
            if stage == WorkflowStage.SCREENING:
                self._schedule_screening(application_id)
            elif stage == WorkflowStage.TEST:
                self._schedule_test(application_id)
            elif stage == WorkflowStage.INTERVIEW:
                self._schedule_interview(application_id)
            elif stage == WorkflowStage.OFFER:
                self._prepare_offer(application_id)
                
        except Exception as e:
            logger.error(f"Error scheduling next steps: {str(e)}")
    
    def _schedule_screening(self, application_id: str):
        """Schedule initial screening"""
        try:
            # Create screening event
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                return
            
            event = ScheduleEvent(
                job_id=application_data["job_id"],
                event_type="Screening",
                title="Initial Application Screening",
                description="Review application and resume for initial qualifications",
                scheduled_datetime=datetime.now() + timedelta(hours=24),
                participants=[application_data["hr_id"]],
                metadata={"application_id": application_id}
            )
            
            self.db.insert_one("schedule_events", event.to_dict())
            
        except Exception as e:
            logger.error(f"Error scheduling screening: {str(e)}")
    
    def _schedule_test(self, application_id: str):
        """Schedule assessment test"""
        try:
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                return
            
            # Check if test exists for this job
            test_data = self.db.find_one("tests", {"job_id": application_data["job_id"], "status": "Active"})
            
            if test_data:
                # Create test submission
                submission_id = test_service.start_test_submission(
                    str(test_data["_id"]),
                    application_id,
                    application_data["user_id"]
                )
                
                # Schedule test event
                event = ScheduleEvent(
                    job_id=application_data["job_id"],
                    event_type="Test",
                    title="Assessment Test",
                    description=f"Complete assessment test for {application_data['applicant_name']}",
                    scheduled_datetime=datetime.now() + timedelta(days=2),
                    participants=[application_data["user_id"], application_data["hr_id"]],
                    metadata={
                        "application_id": application_id,
                        "test_id": str(test_data["_id"]),
                        "submission_id": submission_id
                    }
                )
                
                self.db.insert_one("schedule_events", event.to_dict())
                
                # Send test invitation
                notification_service.send_test_invitation(application_data, test_data)
            
        except Exception as e:
            logger.error(f"Error scheduling test: {str(e)}")
    
    def _schedule_interview(self, application_id: str):
        """Schedule interview"""
        try:
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                return
            
            # Find available HR and time slot
            hr_id = application_data["hr_id"]
            interview_time = self._find_next_available_slot(hr_id)
            
            if interview_time:
                interview_id = interview_service.schedule_interview(
                    application_id=application_id,
                    job_id=application_data["job_id"],
                    candidate_id=application_data["user_id"],
                    hr_id=hr_id,
                    interview_type="Technical",
                    scheduled_datetime=interview_time,
                    duration_minutes=60
                )
                
                # Send interview invitation
                interview_data = self.db.find_one("interviews", {"_id": ObjectId(interview_id)})
                if interview_data:
                    notification_service.send_interview_invitation(application_data, interview_data)
            
        except Exception as e:
            logger.error(f"Error scheduling interview: {str(e)}")
    
    def _prepare_offer(self, application_id: str):
        """Prepare job offer"""
        try:
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                return
            
            # Create offer record
            offer = JobOffer(
                application_id=application_id,
                job_id=application_data["job_id"],
                candidate_id=application_data["user_id"],
                hr_id=application_data["hr_id"],
                status="Draft",
                expiry_date=datetime.now() + timedelta(days=7)
            )
            
            offer_id = self.db.insert_one("job_offers", offer.to_dict())
            
            # Schedule offer preparation
            event = ScheduleEvent(
                job_id=application_data["job_id"],
                event_type="Offer",
                title="Prepare Job Offer",
                description="Prepare and review job offer package",
                scheduled_datetime=datetime.now() + timedelta(hours=48),
                participants=[application_data["hr_id"]],
                metadata={
                    "application_id": application_id,
                    "offer_id": str(offer_id)
                }
            )
            
            self.db.insert_one("schedule_events", event.to_dict())
            
        except Exception as e:
            logger.error(f"Error preparing offer: {str(e)}")
    
    def _find_next_available_slot(self, hr_id: str, preferred_days: int = 3) -> Optional[datetime]:
        """Find next available interview slot for HR"""
        try:
            # Get business hours (9 AM - 5 PM, Monday-Friday)
            now = datetime.now()
            
            for day_offset in range(preferred_days):
                candidate_date = now + timedelta(days=day_offset)
                
                # Skip weekends
                if candidate_date.weekday() >= 5:  # Saturday, Sunday
                    continue
                
                # Check time slots from 9 AM to 4 PM (1-hour slots)
                for hour in range(9, 17):
                    slot_time = candidate_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    # Check if slot is available
                    has_conflict = interview_service.check_interview_conflicts(hr_id, slot_time, 60)
                    
                    if not has_conflict:
                        return slot_time
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding available slot: {str(e)}")
            return None
    
    def _get_next_action(self, stage: WorkflowStage) -> tuple:
        """Get next action and date for a stage"""
        action_mapping = {
            WorkflowStage.APPLIED: ("Initial screening", datetime.now() + timedelta(days=1)),
            WorkflowStage.SCREENING: ("Schedule assessment test", datetime.now() + timedelta(days=2)),
            WorkflowStage.TEST: ("Schedule interview", datetime.now() + timedelta(days=3)),
            WorkflowStage.INTERVIEW: ("Prepare job offer", datetime.now() + timedelta(days=2)),
            WorkflowStage.OFFER: ("Await candidate response", datetime.now() + timedelta(days=7)),
            WorkflowStage.HIRED: ("Onboarding preparation", datetime.now() + timedelta(days=1)),
            WorkflowStage.REJECTED: ("Send rejection notification", datetime.now() + timedelta(hours=24))
        }
        
        return action_mapping.get(stage, ("", None))
    
    def _send_application_confirmation(self, application_data: Dict[str, Any]):
        """Send application confirmation email"""
        try:
            subject = "Application Received - JobSphere"
            body = f"""
            Dear {application_data['applicant_name']},
            
            Thank you for applying for the position. We have received your application and will review it shortly.
            
            Application ID: {application_data['_id']}
            Position: {application_data.get('job_title', 'Not specified')}
            
            You will receive updates on your application status via email.
            
            Best regards,
            The Hiring Team
            """
            
            email_service.send_email(
                application_data['email'],
                subject,
                body
            )
            
        except Exception as e:
            logger.error(f"Error sending application confirmation: {str(e)}")
    
    def _send_stage_notification(self, application_id: str, stage: WorkflowStage):
        """Send stage change notification"""
        try:
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                return
            
            stage_messages = {
                WorkflowStage.SCREENING: "Your application is under initial screening",
                WorkflowStage.TEST: "You have been selected for the assessment test",
                WorkflowStage.INTERVIEW: "Congratulations! You have been selected for an interview",
                WorkflowStage.OFFER: "Great news! We would like to extend a job offer",
                WorkflowStage.HIRED: "Welcome aboard! You have been hired",
                WorkflowStage.REJECTED: "Thank you for your interest, but we will not be proceeding"
            }
            
            message = stage_messages.get(stage, "Your application status has been updated")
            
            subject = f"Application Update - {stage.value}"
            body = f"""
            Dear {application_data['applicant_name']},
            
            {message}.
            
            Application ID: {application_id}
            Current Status: {stage.value}
            
            You will receive further details via email shortly.
            
            Best regards,
            The Hiring Team
            """
            
            email_service.send_email(
                application_data['email'],
                subject,
                body
            )
            
        except Exception as e:
            logger.error(f"Error sending stage notification: {str(e)}")
    
    def _send_test_invitation(self, application_data: Dict[str, Any], test_data: Dict[str, Any]):
        """Send test invitation email"""
        try:
            subject = "Assessment Test Invitation - JobSphere"
            body = f"""
            Dear {application_data['applicant_name']},
            
            You have been selected to take an assessment test for the position you applied for.
            
            Test Details:
            - Test Title: {test_data['title']}
            - Duration: {test_data['duration_minutes']} minutes
            - Passing Score: {test_data['passing_score']}%
            
            Please log in to your account to take the test at your earliest convenience.
            
            Best regards,
            The Hiring Team
            """
            
            email_service.send_email(
                application_data['email'],
                subject,
                body
            )
            
        except Exception as e:
            logger.error(f"Error sending test invitation: {str(e)}")
    
    def _send_interview_invitation(self, application_data: Dict[str, Any], 
                                 interview_id: str, interview_time: datetime):
        """Send interview invitation email"""
        try:
            subject = "Interview Invitation - JobSphere"
            body = f"""
            Dear {application_data['applicant_name']},
            
            Congratulations! We would like to invite you for an interview.
            
            Interview Details:
            - Date: {interview_time.strftime('%A, %B %d, %Y')}
            - Time: {interview_time.strftime('%I:%M %p')}
            - Type: Technical Interview
            - Duration: 60 minutes
            
            Please confirm your attendance by replying to this email.
            
            Best regards,
            The Hiring Team
            """
            
            email_service.send_email(
                application_data['email'],
                subject,
                body
            )
            
        except Exception as e:
            logger.error(f"Error sending interview invitation: {str(e)}")
    
    def get_pipeline_overview(self, job_id: str = None) -> Dict[str, Any]:
        """
        Get overview of candidate pipeline
        
        Args:
            job_id: Optional job ID to filter by
            
        Returns:
            Pipeline overview statistics
        """
        try:
            query = {}
            if job_id:
                query["job_id"] = job_id
            
            pipelines = self.db.find_many("candidate_pipeline", query)
            
            overview = {
                "total_candidates": 0,
                "by_stage": {},
                "conversion_rates": {}
            }
            
            stage_counts = {}
            for pipeline in pipelines:
                # Ensure pipeline has current_stage
                if not isinstance(pipeline, dict):
                    logger.warning(f"Pipeline is not a dictionary: {pipeline}")
                    continue
                
                stage = pipeline.get("current_stage", "Unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
                overview["total_candidates"] += 1
            
            overview["by_stage"] = stage_counts
            
            # Calculate conversion rates
            if overview["total_candidates"] > 0:
                for stage, count in stage_counts.items():
                    overview["conversion_rates"][stage] = (count / overview["total_candidates"]) * 100
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting pipeline overview: {str(e)}")
            # Return a safe default structure
            return {
                "total_candidates": 0,
                "by_stage": {},
                "conversion_rates": {}
            }
    
    def get_pending_actions(self, hr_id: str = None) -> List[Dict[str, Any]]:
        """
        Get pending actions for HR or all HR
        
        Args:
            hr_id: Optional HR ID to filter by
            
        Returns:
            List of pending actions
        """
        try:
            # Get upcoming events
            query = {"status": "Scheduled"}
            if hr_id:
                query["participants"] = hr_id
            
            events_cursor = self.db.find_many(
                "schedule_events",
                query,
                sort=[("scheduled_datetime", 1)]
            )
            
            pending_actions = []
            for event in events_cursor:
                # Get related application data
                # Ensure metadata is a dictionary
                if not isinstance(event.get("metadata"), dict):
                    event["metadata"] = {}
                
                application_id = event["metadata"].get("application_id")
                if application_id:
                    application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
                    event["application"] = application_data
                
                pending_actions.append(event)
            
            return pending_actions
            
        except Exception as e:
            logger.error(f"Error getting pending actions: {str(e)}")
            return []

# Singleton instance
workflow_service = WorkflowService()