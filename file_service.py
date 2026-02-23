# services/file_service.py
import os
from flask import send_file, send_from_directory

class FileService:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
    
    def view_resume(self, filename):
        """View resume inline"""
        resume_path = os.path.join(self.upload_folder, filename)
        if not os.path.exists(resume_path):
            return None
        return send_file(resume_path, mimetype='application/pdf')
    
    def download_resume(self, filename):
        """Download resume as attachment"""
        if not os.path.exists(os.path.join(self.upload_folder, filename)):
            return None
        return send_from_directory(self.upload_folder, filename, as_attachment=True)
    
    def get_resume_path(self, filename):
        """Get full path to resume file"""
        return os.path.join(self.upload_folder, filename)