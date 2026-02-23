# services/email_service.py
from services import emailsent
import smtplib
from email.message import EmailMessage
import ssl
import logging
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sender_email = "fycopractice@gmail.com"
        self.sender_password = os.getenv("EMAIL_PASSWORD", "your_app_password_here")
    
    @staticmethod
    def send_otp_email(email, otp_or_message):
        """
        Send OTP email or notification email.
        Wrapper around the existing emailsent module.
        """
        try:
            emailsent.send_otp_email(email, otp_or_message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send email to {email}: {e}")
            return False
    
    @staticmethod
    def send_notification_email(email, subject, body):
        """
        Send notification email.
        You can extend this with your email sending logic.
        """
        try:
            # For now, use the same OTP function
            full_message = f"{subject}\n\n{body}"
            emailsent.send_otp_email(email, full_message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send notification to {email}: {e}")
            return False
    
    def send_email(self, recipient_email, subject, body, html_content=None):
        """
        Send email with optional HTML content
        """
        try:
            em = EmailMessage()
            em['From'] = self.sender_email
            em['To'] = recipient_email
            em['Subject'] = subject
            
            # Set plain text content
            em.set_content(body)
            
            # Add HTML content if provided
            if html_content:
                em.add_alternative(html_content, subtype='html')
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(self.sender_email, self.sender_password)
                smtp.sendmail(self.sender_email, recipient_email, em.as_string())
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

# Create singleton instance
email_service = EmailService()