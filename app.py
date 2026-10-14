```python
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    jsonify
)

import sqlite3
import os
import uuid

from werkzeug.utils import secure_filename


app = Flask(__name__)

# Read the secret key from Render environment variables
app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is not configured."
    )


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE = os.path.join(BASE_DIR, "database.db")

ALLOWED_EXTENSIONS = {"ppt", "pptx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Limit uploads to 100 MB
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# Database
# --------------------------------------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_id TEXT UNIQUE NOT NULL,
                faculty_name TEXT NOT NULL,
                ppt_filename TEXT
            )
        """)

        conn.commit()

    finally:
        conn.close()


# --------------------------------------------------
# File Validation
# --------------------------------------------------

def allowed_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def generate_unique_filename(original_filename):
    safe_filename = secure_filename(original_filename)

    if not safe_filename or "." not in safe_filename:
        raise ValueError("Invalid filename.")

    extension = safe_filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported PowerPoint file type.")

    return f"{uuid.uuid4().hex}.{extension}"


# --------------------------------------------------
# Home Page
# --------------------------------------------------

@app.route("/")
def home():
    conn = get_db()

    try:
        faculty = conn.execute("""
            SELECT *
            FROM faculty
            ORDER BY faculty_id
        """).fetchall()

    finally:
        conn.close()

    return render_template(
        "upload.html",
        faculty=faculty
    )


# --------------------------------------------------
# Upload or Update PowerPoint
# --------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload():

    faculty_id = request.form.get(
        "faculty_id", ""
    ).strip()

    faculty_name = request.form.get(
        "faculty_name", ""
    ).strip()

    file = request.files.get("presentation")

    # Validate faculty ID
    if not faculty_id:
        flash("Faculty ID is required.")
        return redirect(url_for("home"))

    # Validate faculty name
    if not faculty_name:
        flash("Faculty name is required.")
        return redirect(url_for("home"))

    # Validate file selection
    if not file or not file.filename:
        flash("Please select a PowerPoint file.")
        return redirect(url_for("home"))

    # Validate extension
    if not allowed_file(file.filename):
        flash("Only PPT and PPTX files are allowed.")
        return redirect(url_for("home"))

    # Generate a unique filename to prevent collisions
    try:
        filename = generate_unique_filename(file.filename)
    except ValueError as error:
        flash(str(error))
        return redirect(url_for("home"))

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Save the new file before updating the database.
    # Remove the new file if the database operation fails.
    try:
        file.save(file_path)

        conn = get_db()

        try:
            existing = conn.execute(
                """
                SELECT *
                FROM faculty
                WHERE faculty_id = ?
                """,
                (faculty_id,)
            ).fetchone()

            if existing:
                old_filename = existing["ppt_filename"]

                conn.execute(
                    """
                    UPDATE faculty
                    SET faculty_name = ?,
                        ppt_filename = ?
                    WHERE faculty_id = ?
                    """,
                    (
                        faculty_name,
                        filename,
                        faculty_id
                    )
                )

                message = "Presentation updated successfully."

            else:
                old_filename = None

                conn.execute(
                    """
                    INSERT INTO faculty (
                        faculty_id,
                        faculty_name,
                        ppt_filename
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        faculty_id,
                        faculty_name,
                        filename
                    )
                )

                message = "Presentation uploaded successfully."

            conn.commit()

        finally:
            conn.close()

    except sqlite3.Error:
        if os.path.exists(file_path):
            os.remove(file_path)

        app.logger.exception("Database error during upload.")
        flash("A database error occurred. Please try again.")
        return redirect(url_for("home"))

    except OSError:
        app.logger.exception("File storage error during upload.")

        if os.path.exists(file_path):
            os.remove(file_path)

        flash("Unable to save the PowerPoint file.")
        return redirect(url_for("home"))

    # Delete the previous file only after the database update succeeds.
    if old_filename and old_filename != filename:
        old_path = os.path.join(UPLOAD_FOLDER, old_filename)

        try:
            if os.path.isfile(old_path):
                os.remove(old_path)
        except OSError:
            app.logger.exception(
                "Could not delete the previous presentation file."
            )

    flash(message)
    return redirect(url_for("home"))


# --------------------------------------------------
# Faculty API
# Used by the Raspberry Pi application
# --------------------------------------------------

@app.route("/api/faculty/<faculty_id>", methods=["GET"])
def faculty_api(faculty_id):

    conn = get_db()

    try:
        faculty = conn.execute(
            """
            SELECT faculty_id, faculty_name, ppt_filename
            FROM faculty
            WHERE faculty_id = ?
            """,
            (faculty_id,)
        ).fetchone()

    finally:
        conn.close()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty not found"
        }), 404

    if not faculty["ppt_filename"]:
        return jsonify({
            "success": False,
            "message": "No presentation uploaded"
        }), 404

    return jsonify({
        "success": True,
        "faculty_id": faculty["faculty_id"],
        "faculty_name": faculty["faculty_name"],
        "ppt_filename": faculty["ppt_filename"],
        "download_url": url_for(
            "download",
            filename=faculty["ppt_filename"],
            _external=True
        )
    })


# --------------------------------------------------
# PowerPoint Download
# --------------------------------------------------

@app.route("/download/<filename>", methods=["GET"])
def download(filename):

    # Only allow files with permitted PowerPoint extensions
    if not allowed_file(filename):
        return jsonify({
            "success": False,
            "message": "Invalid file type"
        }), 400

    return send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=True
    )


# --------------------------------------------------
# File Too Large Handler
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):
    return (
        "File too large. Maximum upload size is 100 MB.",
        413
    )


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

init_database()


# --------------------------------------------------
# Local Development
# Render runs this app using Gunicorn
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
```
