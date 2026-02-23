# services/offer_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from jinja2 import Template
import os

from database.models import JobOffer, Application, Job, HR, User
from database.repository import DatabaseRepository
from services.email_service import email_service

logger = logging.getLogger(__name__)

class OfferService:
    """Service for managing job offers and offer letters"""
    
    def __init__(self):
        self.db = DatabaseRepository()
        self.offer_templates = self._load_offer_templates()
    
    def create_offer(self, application_id: str, salary: float = None, 
                    start_date: datetime = None, offer_type: str = "Full-time",
                    benefits: List[str] = None, terms: str = "") -> str:
        """
        Create a new job offer
        
        Args:
            application_id: ID of the application
            salary: Offered salary
            start_date: Proposed start date
            offer_type: Type of employment
            benefits: List of benefits
            terms: Additional terms and conditions
            
        Returns:
            ID of the created offer
        """
        try:
            # Get application details
            application_data = self.db.find_one("applications", {"_id": ObjectId(application_id)})
            if not application_data:
                logger.error(f"Application {application_id} not found")
                raise Exception("Application not found")
            
            # Set default values if not provided
            if not benefits:
                benefits = self._get_default_benefits()
            
            if not start_date:
                start_date = datetime.now() + timedelta(days=30)
            
            if not terms:
                terms = self._get_default_terms()
            
            # Create offer
            offer = JobOffer(
                application_id=application_id,
                job_id=application_data["job_id"],
                candidate_id=application_data["user_id"],
                hr_id=application_data["hr_id"],
                offer_type=offer_type,
                salary=salary,
                start_date=start_date,
                expiry_date=datetime.now() + timedelta(days=7),
                status="Draft",
                terms=terms,
                benefits=benefits
            )
            
            offer_id = self.db.insert_one("job_offers", offer.to_dict())
            
            logger.info(f"Created offer {offer_id} for application {application_id}")
            return str(offer_id)
            
        except Exception as e:
            logger.error(f"Error creating offer: {str(e)}")
            raise
    
    def generate_offer_letter(self, offer_id: str) -> str:
        """
        Generate offer letter content
        
        Args:
            offer_id: ID of the offer
            
        Returns:
            Generated offer letter HTML content
        """
        try:
            # Get offer details with related data
            offer_data = self.get_offer_details(offer_id)
            if not offer_data:
                raise Exception("Offer not found")
            
            # Select appropriate template
            template = self.offer_templates.get("standard", self.offer_templates["default"])
            
            # Render template with offer data
            offer_letter = template.render(
                candidate_name=offer_data["application"]["applicant_name"],
                job_title=offer_data["job"]["title"],
                department=offer_data["job"]["department"],
                salary=offer_data["offer"]["salary"],
                start_date=offer_data["offer"]["start_date"].strftime("%B %d, %Y"),
                offer_type=offer_data["offer"]["offer_type"],
                benefits=offer_data["offer"]["benefits"],
                expiry_date=offer_data["offer"]["expiry_date"].strftime("%B %d, %Y"),
                company_name="JobSphere Company",
                hr_name=offer_data["hr"]["name"],
                hr_title="Hiring Manager",
                current_date=datetime.now().strftime("%B %d, %Y")
            )
            
            return offer_letter
            
        except Exception as e:
            logger.error(f"Error generating offer letter: {str(e)}")
            raise
    
    def send_offer(self, offer_id: str, send_email: bool = True) -> bool:
        """
        Send job offer to candidate
        
        Args:
            offer_id: ID of the offer
            send_email: Whether to send email notification
            
        Returns:
            True if offer sent successfully
        """
        try:
            # Get offer details
            offer_data = self.get_offer_details(offer_id)
            if not offer_data:
                logger.error(f"Offer {offer_id} not found")
                return False
            
            # Generate offer letter
            offer_letter = self.generate_offer_letter(offer_id)
            
            # Update offer status
            self.db.update_one(
                "job_offers",
                {"_id": ObjectId(offer_id)},
                {
                    "status": "Sent",
                    "sent_at": datetime.now()
                }
            )
            
            # Update application status
            self.db.update_one(
                "applications",
                {"_id": ObjectId(offer_data["offer"]["application_id"])},
                {"status": "Offer Sent", "updated_at": datetime.now()}
            )
            
            # Send email if requested
            if send_email:
                self._send_offer_email(offer_data, offer_letter)
            
            logger.info(f"Sent offer {offer_id} to candidate")
            return True
            
        except Exception as e:
            logger.error(f"Error sending offer: {str(e)}")
            return False
    
    def respond_to_offer(self, offer_id: str, response: str, 
                        candidate_notes: str = "") -> bool:
        """
        Process candidate's response to offer
        
        Args:
            offer_id: ID of the offer
            response: Candidate's response (Accepted/Rejected)
            candidate_notes: Optional notes from candidate
            
        Returns:
            True if response processed successfully
        """
        try:
            # Get offer details
            offer_data = self.db.find_one("job_offers", {"_id": ObjectId(offer_id)})
            if not offer_data:
                logger.error(f"Offer {offer_id} not found")
                return False
            
            # Update offer status
            update_data = {
                "status": response,
                "responded_at": datetime.now()
            }
            
            if candidate_notes:
                update_data["candidate_notes"] = candidate_notes
            
            self.db.update_one(
                "job_offers",
                {"_id": ObjectId(offer_id)},
                update_data
            )
            
            # Update application status
            application_status = "Offer Accepted" if response == "Accepted" else "Offer Rejected"
            self.db.update_one(
                "applications",
                {"_id": ObjectId(offer_data["application_id"])},
                {"status": application_status, "updated_at": datetime.now()}
            )
            
            # Update candidate pipeline
            pipeline_stage = "Hired" if response == "Accepted" else "Offer Rejected"
            self._update_candidate_pipeline(offer_data["application_id"], pipeline_stage)
            
            # Send confirmation
            self._send_offer_response_notification(offer_data, response)
            
            logger.info(f"Processed {response.lower()} response for offer {offer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing offer response: {str(e)}")
            return False
    
    def get_offer_details(self, offer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed offer information
        
        Args:
            offer_id: ID of the offer
            
        Returns:
            Offer details with related data
        """
        try:
            # Get offer
            offer_data = self.db.find_one("job_offers", {"_id": ObjectId(offer_id)})
            if not offer_data:
                return None
            
            # Get related data
            application_data = self.db.find_one("applications", {"_id": ObjectId(offer_data["application_id"])})
            job_data = self.db.find_one("jobs", {"_id": ObjectId(offer_data["job_id"])})
            hr_data = self.db.find_one("hrs", {"_id": ObjectId(offer_data["hr_id"])})
            candidate_data = self.db.find_one("users", {"_id": ObjectId(offer_data["candidate_id"])})
            
            # Convert ObjectIds to strings
            offer_data["_id"] = str(offer_data["_id"])
            
            return {
                "offer": offer_data,
                "application": application_data,
                "job": job_data,
                "hr": hr_data,
                "candidate": candidate_data
            }
            
        except Exception as e:
            logger.error(f"Error getting offer details: {str(e)}")
            return None
    
    def get_offers_for_job(self, job_id: str, status: str = None) -> List[Dict[str, Any]]:
        """
        Get all offers for a specific job
        
        Args:
            job_id: ID of the job
            status: Optional status filter
            
        Returns:
            List of offers
        """
        try:
            query = {"job_id": job_id}
            if status:
                query["status"] = status
            
            offers_cursor = self.db.find_many("job_offers", query, sort=[("created_at", -1)])
            
            offers = []
            for offer in offers_cursor:
                # Get related data
                application_data = self.db.find_one("applications", {"_id": ObjectId(offer["application_id"])})
                candidate_data = self.db.find_one("users", {"_id": ObjectId(offer["candidate_id"])})
                
                offer["_id"] = str(offer["_id"])
                offer["application"] = application_data
                offer["candidate"] = candidate_data
                
                offers.append(offer)
            
            return offers
            
        except Exception as e:
            logger.error(f"Error getting offers for job {job_id}: {str(e)}")
            return []
    
    def get_offer_statistics(self, job_id: str = None) -> Dict[str, Any]:
        """
        Get offer statistics
        
        Args:
            job_id: Optional job ID to filter by
            
        Returns:
            Offer statistics
        """
        try:
            query = {}
            if job_id:
                query["job_id"] = job_id
            
            offers = list(self.db.find_many("job_offers", query))
            
            if not offers:
                return {
                    "total_offers": 0,
                    "accepted": 0,
                    "rejected": 0,
                    "pending": 0,
                    "acceptance_rate": 0
                }
            
            total_offers = len(offers)
            accepted = sum(1 for offer in offers if offer["status"] == "Accepted")
            rejected = sum(1 for offer in offers if offer["status"] == "Rejected")
            pending = sum(1 for offer in offers if offer["status"] in ["Sent", "Draft"])
            
            acceptance_rate = (accepted / total_offers * 100) if total_offers > 0 else 0
            
            return {
                "total_offers": total_offers,
                "accepted": accepted,
                "rejected": rejected,
                "pending": pending,
                "acceptance_rate": acceptance_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting offer statistics: {str(e)}")
            return {}
    
    def _load_offer_templates(self) -> Dict[str, Template]:
        """Load offer letter templates"""
        templates = {}
        
        # Default template
        default_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Job Offer Letter</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
        .header { text-align: center; margin-bottom: 30px; }
        .content { max-width: 800px; margin: 0 auto; }
        .signature { margin-top: 50px; }
        .benefits { margin: 20px 0; }
        .benefits ul { list-style-type: none; padding: 0; }
        .benefits li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="content">
        <div class="header">
            <h2>Job Offer Letter</h2>
            <p>{{ current_date }}</p>
        </div>
        
        <p>Dear {{ candidate_name }},</p>
        
        <p>We are pleased to offer you the position of <strong>{{ job_title }}</strong> in the {{ department }} department at {{ company_name }}. This offer is contingent upon successful completion of our standard pre-employment checks.</p>
        
        <h3>Offer Details:</h3>
        <ul>
            <li><strong>Position:</strong> {{ job_title }}</li>
            <li><strong>Department:</strong> {{ department }}</li>
            <li><strong>Employment Type:</strong> {{ offer_type }}</li>
            <li><strong>Start Date:</strong> {{ start_date }}</li>
            <li><strong>Salary:</strong> ${{ salary }} per year</li>
        </ul>
        
        <h3>Benefits:</h3>
        <div class="benefits">
            <ul>
                {% for benefit in benefits %}
                <li>• {{ benefit }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <p>This offer is valid until {{ expiry_date }}. Please review this offer carefully and respond by the expiration date to accept or decline this position.</p>
        
        <p>We are excited about the possibility of you joining our team. If you have any questions, please don't hesitate to contact us.</p>
        
        <div class="signature">
            <p>Sincerely,</p>
            <p><strong>{{ hr_name }}</strong><br>
            {{ hr_title }}<br>
            {{ company_name }}</p>
        </div>
    </div>
</body>
</html>
        """
        
        templates["default"] = Template(default_template)
        templates["standard"] = Template(default_template)
        
        return templates
    
    def _get_default_benefits(self) -> List[str]:
        """Get default benefits list"""
        return [
            "Health, dental, and vision insurance",
            "401(k) retirement plan with company match",
            "Paid time off and holidays",
            "Professional development opportunities",
            "Flexible work arrangements",
            "Company-sponsored life insurance"
        ]
    
    def _get_default_terms(self) -> str:
        """Get default terms and conditions"""
        return """
        This offer is contingent upon:
        1. Successful completion of background check
        2. Verification of credentials and references
        3. Ability to legally work in the country
        4. Signing of employment agreement and confidentiality agreement
        
        Employment is at-will and either party may terminate the employment relationship at any time.
        """
    
    def _send_offer_email(self, offer_data: Dict[str, Any], offer_letter: str):
        """Send offer email to candidate"""
        try:
            subject = f"Job Offer - {offer_data['job']['title']} at JobSphere"
            
            body = f"""
            Dear {offer_data['application']['applicant_name']},
            
            Congratulations! We are pleased to offer you the position of {offer_data['job']['title']}.
            
            Please find the detailed offer letter attached to this email.
            
            Offer Details:
            - Position: {offer_data['job']['title']}
            - Department: {offer_data['job']['department']}
            - Start Date: {offer_data['offer']['start_date'].strftime('%B %d, %Y')}
            - Salary: ${offer_data['offer']['salary']:,} per year
            
            Please review this offer carefully and respond by {offer_data['offer']['expiry_date'].strftime('%B %d, %Y')}.
            
            To accept or decline this offer, please reply to this email with your decision.
            
            We look forward to hearing from you soon!
            
            Best regards,
            {offer_data['hr']['name']}
            Hiring Manager
            JobSphere
            """
            
            email_service.send_email(
                offer_data['application']['email'],
                subject,
                body,
                html_content=offer_letter
            )
            
        except Exception as e:
            logger.error(f"Error sending offer email: {str(e)}")
    
    def _send_offer_response_notification(self, offer_data: Dict[str, Any], response: str):
        """Send notification about offer response"""
        try:
            # Get HR email
            hr_data = self.db.find_one("hrs", {"_id": ObjectId(offer_data["hr_id"])})
            if not hr_data:
                return
            
            subject = f"Offer {response} - {offer_data['application']['applicant_name']}"
            
            body = f"""
            Dear {hr_data['name']},
            
            {offer_data['application']['applicant_name']} has {response.lower()} the job offer for {offer_data['job']['title']}.
            
            Offer Details:
            - Position: {offer_data['job']['title']}
            - Candidate: {offer_data['application']['applicant_name']}
            - Response: {response}
            - Response Date: {datetime.now().strftime('%B %d, %Y')}
            
            Please log in to the system for more details.
            
            Best regards,
            JobSphere System
            """
            
            email_service.send_email(
                hr_data['email'],
                subject,
                body
            )
            
        except Exception as e:
            logger.error(f"Error sending offer response notification: {str(e)}")
    
    def _update_candidate_pipeline(self, application_id: str, stage: str):
        """Update candidate pipeline stage"""
        try:
            self.db.update_one(
                "candidate_pipeline",
                {"application_id": application_id},
                {
                    "current_stage": stage,
                    "updated_at": datetime.now()
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating candidate pipeline: {str(e)}")

# Singleton instance
offer_service = OfferService()