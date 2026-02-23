# services/application_service.py
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from bson import ObjectId
from database.repository import job_repo, app_repo
from database.models import Application, UserActivity
from database.setup import db
import logging

logger = logging.getLogger(__name__)

class ApplicationService:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
    
    def apply_for_job(self, form_data, files, user_id: str):
        """Process job application"""
        try:
            job_id = form_data.get('job_id')
            job = app_repo.find_by_id_and_email(job_id, form_data.get('email'))
            print(job)
            if job is not None:
                return {'error': 'You already applied for this job with the same email.'}
            
            job = job_repo.find_by_id(job_id)
            
            if not job:
                return {'error': 'Job not found'}
            
            # Handle resume upload
            if 'resume' not in files:
                return {'error': 'No resume uploaded'}
            
            file = files['resume']
            if file.filename == '':
                return {'error': 'No selected file'}
            
            # Validate file
            if not self._allowed_file(file.filename):
                return {'error': 'Invalid file type. Only PDF allowed.'}
            
            # Save file
            filename = secure_filename(file.filename)
            unique_name = f"{int(datetime.now().timestamp())}_{filename}"
            file_path = os.path.join(self.upload_folder, unique_name)
            file.save(file_path)
            
            # Create application
            application = Application(
                job_id=job_id,
                user_id=user_id,
                hr_id=job.hr_id,
                applicant_name=form_data.get('name'),
                email=form_data.get('email'),
                phone=form_data.get('phone'),
                cover_letter=form_data.get('cover_letter'),
                resume_file=unique_name
            )
            
            app_id = app_repo.create(application)
            
            # Create user activity
            user_activity = UserActivity(
                user_id=user_id,
                job_id=job_id,
                application_id=app_id,
                status='Pending',
                resume_file=unique_name
            )
            
            db.user_activities.insert_one(user_activity.to_dict(include_id=False))
            
            # Initiate automated hiring workflow
            try:
                from services.workflow_service import workflow_service
                workflow_service.initiate_hiring_workflow(app_id)
            except Exception as workflow_error:
                logger.error(f"Error initiating workflow: {workflow_error}")
                # Don't fail the application if workflow initiation fails
            
            return {'success': True, 'message': 'Application submitted successfully!'}
            
        except Exception as e:
            logger.error(f"Error in apply_for_job: {e}")
            return {'error': str(e)}
    
    def update_application_status(self, app_id: str, status: str, hr_id: str = None):
        """Update application status"""
        success = app_repo.update_status(app_id, status, hr_id)
        return {'success': success}
    
    def get_applications_for_hr_id(self, hr_id: str):
        """Get applications for HR's hr_id"""
        #Change to get applications for HR's hr_id instead of user_id
        applications = app_repo.get_applications_for_hr_id(hr_id)
        return applications
    
    def get_user_applications(self, user_id: str):
        """Get all applications for a user"""
        applications = app_repo.get_user_applications(user_id)
        
        # Enhance with job details
        for app in applications:
            job = job_repo.find_by_id(app.job_id)
            if job:
                app.job_title = job.title
                app.job_department = job.department
        
        return applications
    
    def get_jobs_by_ids(self, job_ids):
        """Get job details for multiple job IDs"""
        try:
            from database.repository import DatabaseRepository
            db = DatabaseRepository()
            
            if not job_ids:
                return []
            
            # Convert string IDs to ObjectId if needed
            object_ids = []
            for job_id in job_ids:
                try:
                    object_ids.append(ObjectId(job_id))
                except:
                    # If it's already an ObjectId string, try to use it directly
                    object_ids.append(job_id)
            
            # Query jobs with the provided IDs
            jobs_cursor = db.find_many("jobs", {"_id": {"$in": object_ids}})
            jobs = []
            
            for job in jobs_cursor:
                job["_id"] = str(job["_id"])
                jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs by IDs: {str(e)}")
            return []
    
    @staticmethod
    def _allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}
# Create singleton instance
application_service = ApplicationService(upload_folder='uploads/resumes')