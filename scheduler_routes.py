# routes/scheduler_routes.py
from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import logging
from bson import ObjectId

from services.test_service import test_service
from services.interview_service import interview_service
from services.workflow_service import workflow_service
from services.offer_service import offer_service
from services.deepseek_service import deepseek_service
from utils.decorators import login_required, hr_required

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')

def serialize_mongo_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_mongo_doc(value)
            elif isinstance(value, list):
                result[key] = [serialize_mongo_doc(item) for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    else:
        return doc

# Test Management Endpoints
@scheduler_bp.route('/tests', methods=['POST'])
@hr_required
def create_test():
    """Create a new test"""
    try:
        data = request.get_json()
        
        test_id = test_service.create_test(
            job_id=data['job_id'],
            title=data['title'],
            description=data['description'],
            duration_minutes=data.get('duration_minutes', 60),
            passing_score=data.get('passing_score', 70)
        )
        
        return jsonify({
            'success': True,
            'test_id': test_id,
            'message': 'Test created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating test: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests/<test_id>/generate-questions', methods=['POST'])
@hr_required
def generate_test_questions(test_id):
    """Generate questions for a test"""
    try:
        data = request.get_json()
        num_questions = data.get('num_questions', 10)
        
        success = test_service.generate_questions_for_test(test_id, num_questions)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Generated {num_questions} questions for test'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate questions'}), 500
            
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests', methods=['GET'])
@hr_required
def get_all_tests():
    """Get all tests"""
    try:
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        
        tests_cursor = db.find_many("tests", {})
        tests = []
        
        for test in tests_cursor:
            test["_id"] = str(test["_id"])
            
            # Get job title
            if "job_id" in test:
                job_data = db.find_one("jobs", {"_id": ObjectId(test["job_id"])})
                test["job_title"] = job_data["title"] if job_data else "N/A"
            
            # Get question count
            questions_count = db.count("questions", {"test_id": test["_id"]})
            test["question_count"] = questions_count
            
            # Get statistics
            stats = test_service.get_test_statistics(test["_id"])
            test.update(stats)
            
            tests.append(test)
        
        return jsonify({
            'success': True,
            'tests': tests
        })
        
    except Exception as e:
        logger.error(f"Error getting all tests: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests/<test_id>', methods=['GET'])
@hr_required
def get_test_details(test_id):
    """Get test details with questions"""
    try:
        test_data = test_service.get_test_with_questions(test_id)
        
        if test_data:
            return jsonify({
                'success': True,
                'test': test_data
            })
        else:
            return jsonify({'success': False, 'error': 'Test not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting test details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests/<test_id>/statistics', methods=['GET'])
@hr_required
def get_test_statistics(test_id):
    """Get test statistics"""
    try:
        stats = test_service.get_test_statistics(test_id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting test statistics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests/<test_id>/submissions', methods=['POST'])
@login_required
def start_test_submission(test_id):
    """Start a test submission"""
    try:
        data = request.get_json()
        
        submission_id = test_service.start_test_submission(
            test_id=test_id,
            application_id=data['application_id'],
            candidate_id=session['user_id']
        )
        
        return jsonify({
            'success': True,
            'submission_id': submission_id,
            'message': 'Test started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error starting test submission: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/test-submissions/<submission_id>/submit', methods=['POST'])
@login_required
def submit_test_answers(submission_id):
    """Submit test answers"""
    try:
        data = request.get_json()
        
        success = test_service.submit_test_answers(
            submission_id=submission_id,
            answers=data['answers']
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Test submitted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to submit test'}), 500
            
    except Exception as e:
        logger.error(f"Error submitting test answers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/test-submissions/<submission_id>/results', methods=['GET'])
@login_required
def get_test_results(submission_id):
    """Get test results"""
    try:
        results = test_service.get_test_results(submission_id)
        
        if results:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({'success': False, 'error': 'Results not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting test results: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/tests/for-application/<application_id>', methods=['GET'])
@login_required
def get_test_for_application(application_id):
    """Get test for a specific application"""
    try:
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        
        # Get application details
        application_data = db.find_one("applications", {"_id": ObjectId(application_id)})
        if not application_data:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get active test for this job
        test_data = db.find_one("tests", {"job_id": application_data["job_id"], "status": "Active"})
        if not test_data:
            return jsonify({'success': False, 'error': 'No test available for this job'}), 404
        
        # Get questions for the test
        test_with_questions = test_service.get_test_with_questions(str(test_data["_id"]))
        
        return jsonify({
            'success': True,
            'test': test_with_questions
        })
        
    except Exception as e:
        logger.error(f"Error getting test for application: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/test-results/application/<application_id>', methods=['GET'])
@login_required
def get_test_results_by_application(application_id):
    """Get test results for a specific application"""
    try:
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        
        # Get test submission for this application
        submission_data = db.find_one("test_submissions", {"application_id": application_id})
        if not submission_data:
            return jsonify({'success': False, 'error': 'No test submission found'}), 404
        
        # Get detailed results
        results = test_service.get_test_results(str(submission_data["_id"]))
        
        if results:
            return jsonify({
                'success': True,
                'results': results
            })
        else:
            return jsonify({'success': False, 'error': 'Results not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting test results for application: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Interview Management Endpoints
@scheduler_bp.route('/interviews', methods=['POST'])
@hr_required
def schedule_interview():
    """Schedule a new interview"""
    try:
        data = request.get_json()
        
        interview_id = interview_service.schedule_interview(
            application_id=data['application_id'],
            job_id=data['job_id'],
            candidate_id=data['candidate_id'],
            hr_id=session['hr_id'],
            interview_type=data['interview_type'],
            scheduled_datetime=datetime.fromisoformat(data['scheduled_datetime']),
            duration_minutes=data.get('duration_minutes', 60),
            meeting_link=data.get('meeting_link'),
            location=data.get('location')
        )
        
        return jsonify({
            'success': True,
            'interview_id': interview_id,
            'message': 'Interview scheduled successfully'
        })
        
    except Exception as e:
        logger.error(f"Error scheduling interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/interviews/<interview_id>', methods=['GET'])
@hr_required
def get_interview_details(interview_id):
    """Get interview details"""
    try:
        interview_data = interview_service.get_interview_details(interview_id)
        
        if interview_data:
            return jsonify({
                'success': True,
                'interview': interview_data
            })
        else:
            return jsonify({'success': False, 'error': 'Interview not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting interview details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/interviews/<interview_id>/status', methods=['PUT'])
@hr_required
def update_interview_status(interview_id):
    """Update interview status"""
    try:
        data = request.get_json()
        
        success = interview_service.update_interview_status(
            interview_id=interview_id,
            status=data['status'],
            notes=data.get('notes')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Interview status updated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update status'}), 500
            
    except Exception as e:
        logger.error(f"Error updating interview status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/interviews/<interview_id>/feedback', methods=['POST'])
@hr_required
def submit_interview_feedback(interview_id):
    """Submit interview feedback"""
    try:
        data = request.get_json()
        
        feedback_id = interview_service.submit_interview_feedback(
            interview_id=interview_id,
            interviewer_id=session['hr_id'],
            technical_skills=data['technical_skills'],
            communication_skills=data['communication_skills'],
            problem_solving=data['problem_solving'],
            cultural_fit=data['cultural_fit'],
            strengths=data.get('strengths', []),
            weaknesses=data.get('weaknesses', []),
            comments=data.get('comments', ''),
            recommendation=data['recommendation']
        )
        
        return jsonify({
            'success': True,
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error submitting interview feedback: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/interviews/hr/<hr_id>', methods=['GET'])
@hr_required
def get_hr_interviews(hr_id):
    """Get interviews for HR"""
    try:
        status = request.args.get('status')
        interviews = interview_service.get_interviews_for_hr(hr_id, status)
        
        return jsonify({
            'success': True,
            'interviews': interviews
        })
        
    except Exception as e:
        logger.error(f"Error getting HR interviews: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/interviews/upcoming', methods=['GET'])
@hr_required
def get_upcoming_interviews():
    """Get upcoming interviews"""
    try:
        days_ahead = int(request.args.get('days', 7))
        interviews = interview_service.get_upcoming_interviews(days_ahead)
        
        return jsonify({
            'success': True,
            'interviews': interviews
        })
        
    except Exception as e:
        logger.error(f"Error getting upcoming interviews: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Workflow Management Endpoints
@scheduler_bp.route('/workflow/initiate/<application_id>', methods=['POST'])
@hr_required
def initiate_workflow(application_id):
    """Initiate hiring workflow for application"""
    try:
        success = workflow_service.initiate_hiring_workflow(application_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow initiated successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to initiate workflow'}), 500
            
    except Exception as e:
        logger.error(f"Error initiating workflow: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/workflow/advance-stage/<application_id>', methods=['POST'])
@hr_required
def advance_candidate_stage(application_id):
    """Advance candidate to next stage"""
    try:
        data = request.get_json()
        
        success = workflow_service.advance_candidate_stage(
            application_id=application_id,
            new_stage=data['new_stage'],
            notes=data.get('notes', ''),
            auto_schedule=data.get('auto_schedule', True)
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Candidate advanced to next stage'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to advance stage'}), 500
            
    except Exception as e:
        logger.error(f"Error advancing candidate stage: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/workflow/pipeline-overview', methods=['GET'])
@hr_required
def get_pipeline_overview():
    """Get pipeline overview"""
    try:
        job_id = request.args.get('job_id')
        overview = workflow_service.get_pipeline_overview(job_id)
        
        return jsonify({
            'success': True,
            'overview': overview
        })
        
    except Exception as e:
        logger.error(f"Error getting pipeline overview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/workflow/pending-actions', methods=['GET'])
@hr_required
def get_pending_actions():
    """Get pending actions"""
    try:
        hr_id = session.get('hr_id')
        actions = workflow_service.get_pending_actions(hr_id)
        
        return jsonify({
            'success': True,
            'actions': actions
        })
        
    except Exception as e:
        logger.error(f"Error getting pending actions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Offer Management Endpoints
@scheduler_bp.route('/offers', methods=['POST'])
@hr_required
def create_offer():
    """Create a new job offer"""
    try:
        data = request.get_json()
        
        offer_id = offer_service.create_offer(
            application_id=data['application_id'],
            salary=data.get('salary'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            offer_type=data.get('offer_type', 'Full-time'),
            benefits=data.get('benefits'),
            terms=data.get('terms')
        )
        
        return jsonify({
            'success': True,
            'offer_id': offer_id,
            'message': 'Offer created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating offer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/<offer_id>/letter', methods=['GET'])
@hr_required
def generate_offer_letter(offer_id):
    """Generate offer letter"""
    try:
        offer_letter = offer_service.generate_offer_letter(offer_id)
        
        return jsonify({
            'success': True,
            'offer_letter': offer_letter
        })
        
    except Exception as e:
        logger.error(f"Error generating offer letter: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/<offer_id>/send', methods=['POST'])
@hr_required
def send_offer(offer_id):
    """Send offer to candidate"""
    try:
        data = request.get_json()
        send_email = data.get('send_email', True)
        
        success = offer_service.send_offer(offer_id, send_email)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Offer sent successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to send offer'}), 500
            
    except Exception as e:
        logger.error(f"Error sending offer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/<offer_id>/respond', methods=['POST'])
@login_required
def respond_to_offer(offer_id):
    """Respond to offer"""
    try:
        data = request.get_json()
        
        success = offer_service.respond_to_offer(
            offer_id=offer_id,
            response=data['response'],
            candidate_notes=data.get('notes', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Offer {data["response"].lower()} successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to process response'}), 500
            
    except Exception as e:
        logger.error(f"Error responding to offer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/<offer_id>', methods=['GET'])
@hr_required
def get_offer_details(offer_id):
    """Get offer details"""
    try:
        offer_data = offer_service.get_offer_details(offer_id)
        
        if offer_data:
            return jsonify({
                'success': True,
                'offer': offer_data
            })
        else:
            return jsonify({'success': False, 'error': 'Offer not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting offer details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/job/<job_id>', methods=['GET'])
@hr_required
def get_job_offers(job_id):
    """Get offers for a job"""
    try:
        status = request.args.get('status')
        offers = offer_service.get_offers_for_job(job_id, status)
        
        return jsonify({
            'success': True,
            'offers': offers
        })
        
    except Exception as e:
        logger.error(f"Error getting job offers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/offers/statistics', methods=['GET'])
@hr_required
def get_offer_statistics():
    """Get offer statistics"""
    try:
        job_id = request.args.get('job_id')
        stats = offer_service.get_offer_statistics(job_id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting offer statistics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# AI-Powered Endpoints
@scheduler_bp.route('/ai/generate-interview-questions/<job_id>', methods=['POST'])
@hr_required
def generate_interview_questions(job_id):
    """Generate interview questions using AI"""
    try:
        data = request.get_json()
        interview_type = data.get('interview_type', 'Technical')
        
        questions = interview_service.generate_interview_questions(job_id, interview_type)
        
        return jsonify({
            'success': True,
            'questions': questions
        })
        
    except Exception as e:
        logger.error(f"Error generating interview questions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/ai/generate-job-description', methods=['POST'])
@hr_required
def generate_job_description():
    """Generate job description using AI"""
    try:
        data = request.get_json()
        
        description = deepseek_service.generate_job_description(
            job_title=data['job_title'],
            department=data['department'],
            skills=data['skills'],
            experience=data['experience']
        )
        
        return jsonify({
            'success': True,
            'description': description
        })
        
    except Exception as e:
        logger.error(f"Error generating job description: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Dashboard Endpoints
@scheduler_bp.route('/dashboard/hr/<hr_id>', methods=['GET'])
@hr_required
def get_hr_dashboard(hr_id):
    """Get HR dashboard data"""
    try:
        logger.debug(f"[DEBUG] Getting HR dashboard for hr_id: {hr_id}")
        
        # Get upcoming interviews
        upcoming_interviews = interview_service.get_upcoming_interviews(7)
        logger.debug(f"[DEBUG] Upcoming interviews type: {type(upcoming_interviews)}")
        
        # Get pending actions
        pending_actions = workflow_service.get_pending_actions(hr_id)
        logger.debug(f"[DEBUG] Pending actions type: {type(pending_actions)}")
        
        # Get pipeline overview
        pipeline_overview = workflow_service.get_pipeline_overview()
        logger.debug(f"[DEBUG] Pipeline overview type: {type(pipeline_overview)}")
        if isinstance(pipeline_overview, dict):
            logger.debug(f"[DEBUG] Pipeline overview keys: {pipeline_overview.keys()}")
        else:
            logger.error(f"[DEBUG] Pipeline overview is not a dict: {pipeline_overview}")
        
        # Get offer statistics
        offer_stats = offer_service.get_offer_statistics()
        logger.debug(f"[DEBUG] Offer stats type: {type(offer_stats)}")
        
        dashboard_data = {
            'upcoming_interviews': serialize_mongo_doc(upcoming_interviews[:5]),  # Limit to 5
            'pending_actions': serialize_mongo_doc(pending_actions[:10]),  # Limit to 10
            'pipeline_overview': serialize_mongo_doc(pipeline_overview),
            'offer_statistics': serialize_mongo_doc(offer_stats),
            'summary': {
                'total_interviews_today': len([i for i in upcoming_interviews
                                              if hasattr(i.get('scheduled_datetime'), 'date') and
                                              i['scheduled_datetime'].date() == datetime.now().date()]),
                'pending_actions_count': len(pending_actions),
                'total_candidates': pipeline_overview.get('total_candidates', 0),
                'offers_to_review': len([o for o in offer_stats if o.get('status') == 'Draft'])
            }
        }
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting HR dashboard: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/dashboard/candidate/<candidate_id>', methods=['GET'])
@login_required
def get_candidate_dashboard(candidate_id):
    """Get candidate dashboard data"""
    try:
        # Get candidate's interviews
        interviews = interview_service.get_candidate_interviews(candidate_id)
        
        # Get candidate's test history
        test_history = test_service.get_candidate_test_history(candidate_id)
        
        # Get candidate's applications
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        applications = list(db.find_many("applications", {"user_id": candidate_id}))
        
        dashboard_data = {
            'interviews': serialize_mongo_doc(interviews),
            'test_history': serialize_mongo_doc(test_history),
            'applications': serialize_mongo_doc(applications),
            'summary': {
                'total_applications': len(applications),
                'upcoming_interviews': len([i for i in interviews if i.get('status') == 'Scheduled']),
                'completed_tests': len([t for t in test_history if t.get('status') == 'Evaluated']),
                'pending_actions': len([i for i in interviews if i.get('status') == 'Scheduled']) +
                                 len([t for t in test_history if t.get('status') == 'In Progress'])
            }
        }
        
        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting candidate dashboard: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Additional endpoints for HR dashboard
@scheduler_bp.route('/hr/applications', methods=['GET'])
@hr_required
def get_hr_applications():
    """Get applications for HR dashboard"""
    try:
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        
        applications_cursor = db.find_many("applications", {})
        applications = []
        
        for app in applications_cursor:
            # Get job details
            if "job_id" in app:
                job_data = db.find_one("jobs", {"_id": ObjectId(app["job_id"])})
                app["job_title"] = job_data["title"] if job_data else "N/A"
            
            applications.append(app)
        
        return jsonify({
            'success': True,
            'applications': serialize_mongo_doc(applications)
        })
        
    except Exception as e:
        logger.error(f"Error getting HR applications: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduler_bp.route('/hr/jobs', methods=['GET'])
@hr_required
def get_hr_jobs():
    """Get jobs for HR dashboard"""
    try:
        from database.repository import DatabaseRepository
        db = DatabaseRepository()
        
        jobs_cursor = db.find_many("jobs", {})
        jobs = list(jobs_cursor)
        
        return jsonify({
            'success': True,
            'jobs': serialize_mongo_doc(jobs)
        })
        
    except Exception as e:
        logger.error(f"Error getting HR jobs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500