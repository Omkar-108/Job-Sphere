# services/job_service.py
from datetime import datetime
from database.repository import job_repo, hr_repo
from database.models import Job
import logging

logger = logging.getLogger(__name__)

class JobService:
    @staticmethod
    def create_job(hr_email: str, job_data: dict):
        """Create a new job posting"""
        hr = hr_repo.find_by_email_or_username(hr_email)
        if not hr:
            return {'error': 'HR not found'}
        
        job = Job(
            hr_id=str(hr._id),
            title=job_data['title'],
            department=hr.department,  # Use HR's department
            location=job_data['location'],
            experience=job_data['experience'],
            skills=job_data['skills'],
            description=job_data['description'],
            hiring_start=datetime.strptime(job_data['start_date'], '%Y-%m-%d'),
            hiring_end=datetime.strptime(job_data['end_date'], '%Y-%m-%d')
        )
        
        job_id = job_repo.create(job)
        return {'success': True, 'job_id': job_id}
    
    @staticmethod
    def update_job(job_id: str, hr_email: str, update_data: dict):
        """Update a job posting"""
        hr = hr_repo.find_by_email_or_username(hr_email)
        if not hr:
            return {'error': 'HR not found'}
        
        # Verify HR owns this job
        job = job_repo.find_by_id(job_id)
        if not job or job.hr_id != str(hr._id):
            return {'error': 'Job not found or unauthorized'}
        
        # Prepare update data
        if 'start_date' in update_data:
            update_data['hiring_start'] = datetime.strptime(update_data.pop('start_date'), '%Y-%m-%d')
        if 'end_date' in update_data:
            update_data['hiring_end'] = datetime.strptime(update_data.pop('end_date'), '%Y-%m-%d')
        
        success = job_repo.update(job_id, update_data)
        return {'success': success}
    
    @staticmethod
    def delete_job(job_id: str, hr_email: str):
        """Delete a job posting"""
        hr = hr_repo.find_by_email_or_username(hr_email)
        if not hr:
            return {'error': 'HR not found'}
        
        # Verify HR owns this job
        job = job_repo.find_by_id(job_id)
        if not job or job.hr_id != str(hr._id):
            return {'error': 'Job not found or unauthorized'}
        
        success = job_repo.delete(job_id)
        return {'success': success}
    
    @staticmethod
    def get_all_jobs():
        """Get all active job postings"""
        jobs = job_repo.get_all_jobs()
        return [job.to_dict() for job in jobs]
    
    @staticmethod
    def get_job_by_id(job_id: str):
        """Get job by ID"""
        job = job_repo.find_by_id(job_id)
        return job.to_dict() if job else None
    
    @staticmethod
    def get_hr_jobs(hr_email: str):
        """Get all jobs for an HR"""
        hr = hr_repo.find_by_email_or_username(hr_email)
        if not hr:
            return []
        
        jobs = job_repo.find_by_hr(str(hr._id))
        return [job.to_dict() for job in jobs]

job_service = JobService()