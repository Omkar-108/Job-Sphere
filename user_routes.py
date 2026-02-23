# routes/user_routes.py
from flask import Blueprint, render_template, session, redirect, url_for
from services import application_service
from services.file_service import FileService
from utils.decorators import require_user
import os

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard/user')
@require_user
def dashboard_user():
    user_id = session.get('user_id')
    
    # Use application_service singleton and create FileService instance
    app_service = application_service
    file_svc = FileService('uploads/resumes')  # Use same upload folder as application_service
    
    applications = app_service.get_user_applications(user_id)
    job_ids = [app.job_id for app in applications]
    job_details = app_service.get_jobs_by_ids(job_ids)
    applications = [app.to_dict() for app in applications]
    applications_with_jobs = zip(applications, job_details)
    
    return render_template(
        "dashboard_user.html",
        applications_with_jobs=applications_with_jobs,
        user_email=session.get('email'),
        session=session,
        user_id=user_id
    )

@user_bp.route('/video/user/<app_id>')
@require_user
def video_call_user(app_id):
    return render_template("video_call_user.html", app_id=app_id)