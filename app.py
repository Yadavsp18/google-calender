"""
Google Calendar Meeting Creator - Flask Application
Main entry point for the web application.

This module orchestrates:
- Route registration
- App configuration

For business logic, see:
- services/calendar.py - Calendar operations
- services/auth.py - Authentication
- routes/auth.py - Auth routes
- routes/meetings.py - Meeting routes

For NLP processing, see:
- modules/datetime_utils.py - Date/time parsing
- modules/meeting_extractor.py - Meeting extraction
"""

from flask import Flask, request, jsonify, render_template, send_file
import os

from routes.auth import auth_bp
from routes.meetings import meetings_bp
from routes.chats import chats_bp
from config import get_credentials_path


# =============================================================================
# App Configuration
# =============================================================================

app = Flask(__name__)
app.secret_key = 'super-secret-fixed-key-78910'


# =============================================================================
# Context Processors - Inject API key into all templates
# =============================================================================

@app.context_processor
def inject_api_key():
    """Make API key available to all templates."""
    import json
    creds_file = get_credentials_path()
    api_key = ''
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key', '')
    except Exception:
        api_key = ''
    return dict(DEVELOPER_KEY=api_key)


# =============================================================================
# Register Blueprints
# =============================================================================

app.register_blueprint(auth_bp)
app.register_blueprint(meetings_bp, url_prefix='')
app.register_blueprint(chats_bp, url_prefix='')

# =============================================================================
# Excel Conversion Routes
# =============================================================================

from modules.excel_converter import convert_excel_to_json

ALLOWED_EXTENSIONS = {"xls", "xlsx"}
UPLOAD_FOLDER = "uploads"
JSON_FOLDER = "json_files"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["JSON_FOLDER"] = JSON_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/convert", methods=["POST"])
def convert():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"status": "error", "message": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"status": "error", "message": "Invalid file type. Only .xls and .xlsx are allowed."}), 400

        json_file = convert_excel_to_json(file)

        return jsonify({"status": "success", "json_file": json_file}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/download/<filename>")
def download_file(filename):
    return send_file(
        os.path.join(app.config["JSON_FOLDER"], filename),
        as_attachment=True,
        download_name=filename
    )


@app.route("/excel-converter")
def excel_converter():
    """Render the Excel to JSON converter page."""
    return render_template("excel_converter.html")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
