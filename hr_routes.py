# routes/hr_routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from services import job_service, application_service, auth_service, file_service
from services.file_service import FileService
from database.repository import hr_repo, job_repo
from utils.decorators import require_hr
import os
from datetime import datetime

hr_bp = Blueprint('hr', __name__)

@hr_bp.route('/dashboard/hr')
@require_hr
def dashboard_hr():
    hr_email = session.get('email')
    hr = hr_repo.find_by_email_or_username(hr_email)
    
    if not hr:
        return redirect(url_for('auth.login_page'))
    
    # Initialize services
    app_service = application_service
    file_service = FileService('uploads/resume')
    
    # Get applications for HR's department
    applications = app_service.get_applications_for_hr_id(str(hr._id))
    
    # Count stats
    total_jobs = job_repo.find_by_hr(str(hr._id))
    total_apps = len(applications)
    interviews = sum(1 for app in applications if app.status == 'Interview Scheduled')
    hired = sum(1 for app in applications if app.status == 'Hired')
    job = job_repo.find_by_id(applications[0].job_id) if applications else None
    
    dashboard_data = {
        'total_openings': len(total_jobs),
        'total_applications': total_apps,
        'interviews': interviews,
        'hired_candidates': hired
    }

    return render_template(
        'dashboard_hr.html',
        data=dashboard_data,
        applications=applications[:10],
        job=job,
        user_email=hr_email
    )

@hr_bp.route('/dashboard/scheduler')
@require_hr
def dashboard_scheduler():
    """HR Scheduler Dashboard"""
    hr_email = session.get('email')
    hr = hr_repo.find_by_email_or_username(hr_email)
    jobs = job_repo.find_by_hr(str(hr._id))
    
    if not hr:
        return redirect(url_for('auth.login_page'))
    
    return render_template(
        'dashboard_scheduler.html',
        jobs=jobs,
        hr_name=hr.name,
        hr_id=str(hr._id)
    )

@hr_bp.route('/hr/jobs/add', methods=['GET'])
@require_hr
def hr_add_job_page():
    return render_template('hr_add_job.html')

@hr_bp.route('/hr/jobs/add', methods=['POST'])
@require_hr
def hr_add_job():
    hr_email = session.get('email')
    result = job_service.create_job(hr_email, request.form)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return redirect(url_for('hr.hr_jobs_manage'))

@hr_bp.route('/hr/jobs/manage')
@require_hr
def hr_jobs_manage():
    hr_email = session.get('email')
    jobs = job_service.get_hr_jobs(hr_email)
    return render_template('hr_jobs_manage.html', jobs=jobs)

@hr_bp.route('/hr/jobs/edit/<job_id>', methods=['GET'])
@require_hr
def hr_edit_job_page(job_id):
    job = job_service.get_job_by_id(job_id)
    if not job:
        from flask import abort
        abort(404)
    return render_template('hr_edit_job.html', job=job)

@hr_bp.route('/hr/jobs/edit/<job_id>', methods=['POST'])
@require_hr
def hr_edit_job(job_id):
    hr_email = session.get('email')
    result = job_service.update_job(job_id, hr_email, request.form)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return redirect(url_for('hr.hr_jobs_manage'))

@hr_bp.route('/hr/jobs/delete/<job_id>')
@require_hr
def hr_delete_job(job_id):
    hr_email = session.get('email')
    result = job_service.delete_job(job_id, hr_email)
    
    if 'error' in result:
        from flask import flash
        flash(result['error'], 'error')
    
    return redirect(url_for('hr.hr_jobs_manage'))

@hr_bp.route('/update_status/<app_id>', methods=['POST'])
@require_hr
def update_status(app_id):
    new_status = request.form.get('status')
    hr_email = session.get('email')
    hr = hr_repo.find_by_email_or_username(hr_email)
    
    if not hr:
        return redirect(url_for('auth.login_page'))
    
    app_service = app_service
    result = app_service.update_application_status(app_id, new_status, str(hr._id))
    
    return redirect(url_for('hr.dashboard_hr'))

@hr_bp.route("/video/<app_id>")
@require_hr
def video_call(app_id):
    return render_template("video_call.html", app_id=app_id)

@hr_bp.route("/interview-management")
@require_hr
def interview_management():
    return render_template("interview_management.html")

@hr_bp.route("/offer-management")
@require_hr
def offer_management():
    return render_template("offer_management.html")