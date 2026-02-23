# services/notification_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId

from database.models import EmailTemplate, EmailLog
from database.repository import DatabaseRepository
from services.email_service import email_service

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing all email notifications in the hiring process"""
    
    def __init__(self):
        self.db = DatabaseRepository()
        self._initialize_default_templates()
    
    def send_application_confirmation(self, application_data: Dict[str, Any]) -> bool:
        """Send application confirmation email"""
        try:
            template = self._get_template("Application Confirmation")
            if not template:
                return self._send_fallback_confirmation(application_data)
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'application_id': str(application_data['_id']),
                'company_name': 'JobSphere',
                'current_date': datetime.now().strftime('%B %d, %Y')
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {'application_id': str(application_data['_id'])}
            )
            
        except Exception as e:
            logger.error(f"Error sending application confirmation: {str(e)}")
            return False
    
    def send_test_invitation(self, application_data: Dict[str, Any], test_data: Dict[str, Any]) -> bool:
        """Send test invitation email"""
        try:
            template = self._get_template("Test Invitation")
            if not template:
                return self._send_fallback_test_invitation(application_data, test_data)
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'test_title': test_data['title'],
                'test_duration': test_data['duration_minutes'],
                'passing_score': test_data['passing_score'],
                'test_link': f"{self._get_base_url()}/candidate/test/{test_data['_id']}",
                'expiry_date': (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'),
                'company_name': 'JobSphere'
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(application_data['_id']),
                    'test_id': str(test_data['_id'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending test invitation: {str(e)}")
            return False
    
    def send_interview_invitation(self, application_data: Dict[str, Any], 
                                interview_data: Dict[str, Any]) -> bool:
        """Send interview invitation email"""
        try:
            template = self._get_template("Interview Invitation")
            if not template:
                return self._send_fallback_interview_invitation(application_data, interview_data)
            
            interview_datetime = datetime.fromisoformat(interview_data['scheduled_datetime'])
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'interview_type': interview_data['interview_type'],
                'interview_date': interview_datetime.strftime('%A, %B %d, %Y'),
                'interview_time': interview_datetime.strftime('%I:%M %p'),
                'interview_duration': interview_data['duration_minutes'],
                'meeting_link': interview_data.get('meeting_link', ''),
                'location': interview_data.get('location', ''),
                'interviewer_name': interview_data.get('hr_name', 'Hiring Manager'),
                'company_name': 'JobSphere'
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(application_data['_id']),
                    'interview_id': str(interview_data['_id'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending interview invitation: {str(e)}")
            return False
    
    def send_offer_letter(self, offer_data: Dict[str, Any], offer_letter_html: str) -> bool:
        """Send job offer email with offer letter"""
        try:
            template = self._get_template("Offer Letter")
            if not template:
                return self._send_fallback_offer(offer_data, offer_letter_html)
            
            variables = {
                'candidate_name': offer_data['application']['applicant_name'],
                'job_title': offer_data['job']['title'],
                'salary': f"${offer_data['offer']['salary']:,.0f}",
                'start_date': offer_data['offer']['start_date'].strftime('%B %d, %Y'),
                'offer_type': offer_data['offer']['offer_type'],
                'expiry_date': offer_data['offer']['expiry_date'].strftime('%B %d, %Y'),
                'hr_name': offer_data['hr']['name'],
                'company_name': 'JobSphere'
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                offer_data['application']['email'],
                offer_data['application']['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(offer_data['offer']['application_id']),
                    'offer_id': str(offer_data['offer']['_id']),
                    'html_content': offer_letter_html
                },
                html_content=offer_letter_html
            )
            
        except Exception as e:
            logger.error(f"Error sending offer letter: {str(e)}")
            return False
    
    def send_rejection_notification(self, application_data: Dict[str, Any], 
                                  stage: str = "Application") -> bool:
        """Send rejection notification"""
        try:
            template = self._get_template("Rejection Notification")
            if not template:
                return self._send_fallback_rejection(application_data, stage)
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'rejection_stage': stage,
                'company_name': 'JobSphere',
                'current_date': datetime.now().strftime('%B %d, %Y')
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(application_data['_id']),
                    'rejection_stage': stage
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending rejection notification: {str(e)}")
            return False
    
    def send_interview_reminder(self, application_data: Dict[str, Any], 
                              interview_data: Dict[str, Any]) -> bool:
        """Send interview reminder email"""
        try:
            template = self._get_template("Interview Reminder")
            if not template:
                return self._send_fallback_reminder(application_data, interview_data)
            
            interview_datetime = datetime.fromisoformat(interview_data['scheduled_datetime'])
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'interview_type': interview_data['interview_type'],
                'interview_date': interview_datetime.strftime('%A, %B %d, %Y'),
                'interview_time': interview_datetime.strftime('%I:%M %p'),
                'meeting_link': interview_data.get('meeting_link', ''),
                'location': interview_data.get('location', ''),
                'company_name': 'JobSphere'
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(application_data['_id']),
                    'interview_id': str(interview_data['_id'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending interview reminder: {str(e)}")
            return False
    
    def send_welcome_email(self, application_data: Dict[str, Any]) -> bool:
        """Send welcome email to hired candidate"""
        try:
            template = self._get_template("Welcome Email")
            if not template:
                return self._send_fallback_welcome(application_data)
            
            variables = {
                'candidate_name': application_data['applicant_name'],
                'job_title': application_data.get('job_title', 'Position'),
                'start_date': (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y'),
                'company_name': 'JobSphere',
                'current_date': datetime.now().strftime('%B %d, %Y')
            }
            
            subject = self._render_template(template['subject'], variables)
            body = self._render_template(template['body'], variables)
            
            return self._send_and_log(
                application_data['email'],
                application_data['applicant_name'],
                subject,
                body,
                template['_id'],
                {
                    'application_id': str(application_data['_id'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return False
    
    def _get_template(self, template_type: str) -> Optional[Dict[str, Any]]:
        """Get email template by type"""
        try:
            template_data = self.db.find_one("email_templates", {
                "template_type": template_type,
                "is_active": True
            })
            return template_data
        except Exception as e:
            logger.error(f"Error getting template {template_type}: {str(e)}")
            return None
    
    def _render_template(self, template_str: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        try:
            from jinja2 import Template
            template = Template(template_str)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return template_str
    
    def _send_and_log(self, recipient_email: str, recipient_name: str,
                     subject: str, body: str, template_id: str = None,
                     metadata: Dict[str, Any] = None, html_content: str = None) -> bool:
        """Send email and log the result"""
        try:
            # Send email
            success = email_service.send_email(
                recipient_email,
                subject,
                body,
                html_content=html_content
            )
            
            # Log the email
            email_log = EmailLog(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                template_id=template_id,
                status="Sent" if success else "Failed",
                metadata=metadata or {}
            )
            
            if not success:
                email_log.error_message = "Email service failed to send"
            
            self.db.insert_one("email_logs", email_log.to_dict())
            
            return success
            
        except Exception as e:
            logger.error(f"Error in _send_and_log: {str(e)}")
            
            # Log the failure
            email_log = EmailLog(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                template_id=template_id,
                status="Failed",
                error_message=str(e),
                metadata=metadata or {}
            )
            
            try:
                self.db.insert_one("email_logs", email_log.to_dict())
            except:
                pass  # Don't fail if logging fails
            
            return False
    
    def _initialize_default_templates(self):
        """Initialize default email templates if they don't exist"""
        try:
            default_templates = [
                {
                    "name": "Application Confirmation",
                    "template_type": "Application Confirmation",
                    "subject": "Application Received - {{ job_title }} at {{ company_name }}",
                    "body": """
Dear {{ candidate_name }},

Thank you for applying for the {{ job_title }} position at {{ company_name }}. We have successfully received your application.

Application Details:
- Application ID: {{ application_id }}
- Position: {{ job_title }}
- Date Submitted: {{ current_date }}

Our hiring team will review your application and contact you within 3-5 business days if your profile matches our requirements.

You can check the status of your application by logging into your account.

Best regards,
The Hiring Team
{{ company_name }}
                    """,
                    "variables": ["candidate_name", "job_title", "application_id", "company_name", "current_date"]
                },
                {
                    "name": "Test Invitation",
                    "template_type": "Test Invitation",
                    "subject": "Assessment Test Invitation - {{ job_title }}",
                    "body": """
Dear {{ candidate_name }},

Congratulations! Based on your application for the {{ job_title }} position, we would like to invite you to take an assessment test.

Test Details:
- Test Title: {{ test_title }}
- Duration: {{ test_duration }} minutes
- Passing Score: {{ passing_score }}%
- Deadline: {{ expiry_date }}

Please click the link below to access the test:
{{ test_link }}

Important Notes:
- Ensure you have a stable internet connection
- Complete the test in one session
- The test will automatically submit when time expires

Good luck!

Best regards,
The Hiring Team
{{ company_name }}
                    """,
                    "variables": ["candidate_name", "job_title", "test_title", "test_duration", "passing_score", "test_link", "expiry_date", "company_name"]
                },
                {
                    "name": "Interview Invitation",
                    "template_type": "Interview Invitation",
                    "subject": "Interview Invitation - {{ job_title }} at {{ company_name }}",
                    "body": """
Dear {{ candidate_name }},

Congratulations! We are pleased to invite you for an interview for the {{ job_title }} position.

Interview Details:
- Date: {{ interview_date }}
- Time: {{ interview_time }}
- Duration: {{ interview_duration }} minutes
- Type: {{ interview_type }}

{% if meeting_link %}
Meeting Link: {{ meeting_link }}
{% endif %}

{% if location %}
Location: {{ location }}
{% endif %}

Interviewer: {{ interviewer_name }}

Please confirm your attendance by replying to this email at least 24 hours before the scheduled time.

If you need to reschedule, please let us know as soon as possible.

We look forward to speaking with you!

Best regards,
{{ interviewer_name }}
{{ company_name }}
                    """,
                    "variables": ["candidate_name", "job_title", "interview_date", "interview_time", "interview_duration", "interview_type", "meeting_link", "location", "interviewer_name", "company_name"]
                },
                {
                    "name": "Offer Letter",
                    "template_type": "Offer Letter",
                    "subject": "Job Offer - {{ job_title }} at {{ company_name }}",
                    "body": """
Dear {{ candidate_name }},

We are delighted to offer you the position of {{ job_title }} at {{ company_name }}!

Offer Details:
- Position: {{ job_title }}
- Employment Type: {{ offer_type }}
- Start Date: {{ start_date }}
- Salary: {{ salary }} per year

Please find the detailed offer letter attached to this email. We kindly ask you to review the offer and respond by {{ expiry_date }}.

To accept this offer, please reply to this email with your acceptance and any questions you may have.

We are excited about the possibility of you joining our team!

Best regards,
{{ hr_name }}
{{ company_name }}
                    """,
                    "variables": ["candidate_name", "job_title", "offer_type", "start_date", "salary", "expiry_date", "hr_name", "company_name"]
                },
                {
                    "name": "Rejection Notification",
                    "template_type": "Rejection Notification",
                    "subject": "Update on your {{ job_title }} application",
                    "body": """
Dear {{ candidate_name }},

Thank you for your interest in the {{ job_title }} position at {{ company_name }} and for taking the time to interview with us.

After careful consideration of all candidates, we have decided to move forward with other candidates whose qualifications and experience more closely match our current needs.

This decision was made at the {{ rejection_stage }} stage. We appreciate your interest in {{ company_name }} and wish you the best in your job search.

We will keep your resume on file for future opportunities that may be a better fit.

Best regards,
The Hiring Team
{{ company_name }}
                    """,
                    "variables": ["candidate_name", "job_title", "company_name", "rejection_stage"]
                }
            ]
            
            for template_data in default_templates:
                existing = self.db.find_one("email_templates", {
                    "template_type": template_data["template_type"]
                })
                
                if not existing:
                    template = EmailTemplate(
                        name=template_data["name"],
                        subject=template_data["subject"],
                        body=template_data["body"],
                        template_type=template_data["template_type"],
                        variables=template_data["variables"]
                    )
                    self.db.insert_one("email_templates", template.to_dict())
            
        except Exception as e:
            logger.error(f"Error initializing default templates: {str(e)}")
    
    def _get_base_url(self) -> str:
        """Get base URL for the application"""
        # This should be configured based on your deployment
        return "http://localhost:5000"
    
    # Fallback methods if templates are not available
    def _send_fallback_confirmation(self, application_data: Dict[str, Any]) -> bool:
        """Fallback application confirmation"""
        subject = f"Application Received - {application_data.get('job_title', 'Position')}"
        body = f"""
Dear {application_data['applicant_name']},

Thank you for your application. We have received it and will review it shortly.

Application ID: {application_data['_id']}

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )
    
    def _send_fallback_test_invitation(self, application_data: Dict[str, Any], 
                                     test_data: Dict[str, Any]) -> bool:
        """Fallback test invitation"""
        subject = "Assessment Test Invitation"
        body = f"""
Dear {application_data['applicant_name']},

You have been selected for an assessment test. Please log in to your account to take the test.

Test: {test_data['title']}
Duration: {test_data['duration_minutes']} minutes

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )
    
    def _send_fallback_interview_invitation(self, application_data: Dict[str, Any], 
                                          interview_data: Dict[str, Any]) -> bool:
        """Fallback interview invitation"""
        interview_datetime = datetime.fromisoformat(interview_data['scheduled_datetime'])
        subject = "Interview Invitation"
        body = f"""
Dear {application_data['applicant_name']},

You are invited for an interview on {interview_datetime.strftime('%B %d, %Y at %I:%M %p')}.

Please confirm your attendance.

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )
    
    def _send_fallback_offer(self, offer_data: Dict[str, Any], 
                           offer_letter_html: str) -> bool:
        """Fallback offer email"""
        subject = f"Job Offer - {offer_data['job']['title']}"
        body = f"""
Dear {offer_data['application']['applicant_name']},

We are pleased to offer you the position of {offer_data['job']['title']}.

Please find the detailed offer attached.

Best regards,
{offer_data['hr']['name']}
        """
        return self._send_and_log(
            offer_data['application']['email'],
            offer_data['application']['applicant_name'],
            subject,
            body,
            html_content=offer_letter_html
        )
    
    def _send_fallback_rejection(self, application_data: Dict[str, Any], 
                               stage: str) -> bool:
        """Fallback rejection notification"""
        subject = "Update on your application"
        body = f"""
Dear {application_data['applicant_name']},

Thank you for your interest. We have decided to move forward with other candidates at this time.

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )
    
    def _send_fallback_reminder(self, application_data: Dict[str, Any], 
                              interview_data: Dict[str, Any]) -> bool:
        """Fallback interview reminder"""
        interview_datetime = datetime.fromisoformat(interview_data['scheduled_datetime'])
        subject = "Interview Reminder"
        body = f"""
Dear {application_data['applicant_name']},

This is a reminder about your interview scheduled for {interview_datetime.strftime('%B %d, %Y at %I:%M %p')}.

We look forward to speaking with you.

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )
    
    def _send_fallback_welcome(self, application_data: Dict[str, Any]) -> bool:
        """Fallback welcome email"""
        subject = "Welcome to the team!"
        body = f"""
Dear {application_data['applicant_name']},

Welcome aboard! We are excited to have you join our team.

Best regards,
The Hiring Team
        """
        return self._send_and_log(
            application_data['email'],
            application_data['applicant_name'],
            subject,
            body
        )

# Singleton instance
notification_service = NotificationService()