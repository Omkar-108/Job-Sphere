# routes/video_routes.py
from flask import Blueprint, render_template, session
from utils.decorators import require_hr, require_user
from services.video_service import video_service

video_bp = Blueprint('video', __name__)

# Video call pages
@video_bp.route("/video/<app_id>")
@require_hr
def video_call(app_id):
    return render_template("video_call.html", app_id=app_id)

@video_bp.route("/video/user/<app_id>")
@require_user
def video_call_user(app_id):
    return render_template("video_call_user.html", app_id=app_id)

# Note: WebSocket handlers will be registered in app.py
# because they need the Sock instance directly

# Fallback page for Jitsi meetings
@video_bp.route('/video-fallback/<app_id>')
def video_fallback(app_id):
    # This renders your new HTML page
    # You can also pass the Jitsi URL here if you want it displayed on this page
    jitsi_url = f"https://meet.jit.si{app_id}"
    return render_template('fallback.html', jitsi_url=jitsi_url)