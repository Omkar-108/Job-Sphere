from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import os
import logging

logger = logging.getLogger(__name__)
style_bp = Blueprint('style', __name__)

@style_bp.route("/static/css/style.css", methods=["GET"])
def style_css():
    try:
        static_folder = current_app.static_folder
        file_path = os.path.join(static_folder, "css", "style.css")
        logger.info(f"Static folder: {static_folder}")
        logger.info(f"Looking for file: {file_path}")
        logger.info(f"File exists: {os.path.exists(file_path)}")
        return current_app.send_static_file("css/style.css")
    except Exception as e:
        logger.error(f"Error serving CSS: {e}")
        raise

@style_bp.route("/static/css/style.css.map", methods=["GET"])
def style_css_map():
    try:
        return current_app.send_static_file("css/style.css.map")
    except Exception as e:
        logger.error(f"Error serving CSS map: {e}")
        raise