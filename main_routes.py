# routes/main_routes.py
from flask import Blueprint, render_template
from services.job_service import job_service

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/jobs')
def jobs_page():
    jobs = job_service.get_all_jobs()
    return render_template('jobs.html', jobs=jobs)

@main_bp.route('/jobs/<job_id>')
def job_detail(job_id):
    job = job_service.get_job_by_id(job_id)
    if not job:
        from flask import abort
        abort(404)
    return render_template('job-detail.html', job=job)