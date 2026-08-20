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

import os
import psycopg
from psycopg.rows import dict_row

from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = "presentation-system-secret"


# --------------------------------------------------
# Configuration
# --------------------------------------------------

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"ppt", "pptx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# PostgreSQL Database
# --------------------------------------------------

def get_db():

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    conn = psycopg.connect(
        database_url,
        row_factory=dict_row
    )

    return conn


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

def init_database():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            faculty_id TEXT UNIQUE NOT NULL,
            faculty_name TEXT NOT NULL,
            ppt_filename TEXT
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# File Validation
# --------------------------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# --------------------------------------------------
# Home Page
# --------------------------------------------------

@app.route("/")
def home():

    conn = get_db()

    faculty = conn.execute("""
        SELECT *
        FROM faculty
        ORDER BY faculty_id
    """).fetchall()

    conn.close()

    return render_template(
        "upload.html",
        faculty=faculty
    )


# --------------------------------------------------
# Upload PPT
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


    # ----------------------------------------------
    # Validate Faculty ID
    # ----------------------------------------------

    if not faculty_id:

        flash("Faculty ID is required.")

        return redirect(url_for("home"))


    # ----------------------------------------------
    # Validate Faculty Name
    # ----------------------------------------------

    if not faculty_name:

        flash("Faculty name is required.")

        return redirect(url_for("home"))


    # ----------------------------------------------
    # Validate File
    # ----------------------------------------------

    if not file or file.filename == "":

        flash("Please select a PowerPoint file.")

        return redirect(url_for("home"))


    # ----------------------------------------------
    # Validate Extension
    # ----------------------------------------------

    if not allowed_file(file.filename):

        flash("Only PPT and PPTX files are allowed.")

        return redirect(url_for("home"))


    filename = secure_filename(file.filename)


    conn = get_db()


    # ----------------------------------------------
    # Check Existing Faculty
    # ----------------------------------------------

    existing = conn.execute(
        """
        SELECT *
        FROM faculty
        WHERE faculty_id = %s
        """,
        (faculty_id,)
    ).fetchone()


    # ----------------------------------------------
    # Existing Faculty
    # ----------------------------------------------

    if existing:

        old_filename = existing["ppt_filename"]


        # Delete old local PPT
        if old_filename:

            old_path = os.path.join(
                UPLOAD_FOLDER,
                old_filename
            )

            if os.path.exists(old_path):

                os.remove(old_path)


        # Save new PPT locally for now
        file.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )


        # Update PostgreSQL
        conn.execute(
            """
            UPDATE faculty
            SET faculty_name = %s,
                ppt_filename = %s
            WHERE faculty_id = %s
            """,
            (
                faculty_name,
                filename,
                faculty_id
            )
        )

        flash(
            "Presentation updated successfully."
        )


    # ----------------------------------------------
    # New Faculty
    # ----------------------------------------------

    else:

        # Save PPT locally for now
        file.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )


        # Insert into PostgreSQL
        conn.execute(
            """
            INSERT INTO faculty
            (
                faculty_id,
                faculty_name,
                ppt_filename
            )
            VALUES (%s, %s, %s)
            """,
            (
                faculty_id,
                faculty_name,
                filename
            )
        )

        flash(
            "Presentation uploaded successfully."
        )


    conn.commit()
    conn.close()


    return redirect(url_for("home"))


# --------------------------------------------------
# Faculty API
# Raspberry Pi will use this later
# --------------------------------------------------

@app.route("/api/faculty/<faculty_id>")
def faculty_api(faculty_id):

    conn = get_db()

    faculty = conn.execute(
        """
        SELECT *
        FROM faculty
        WHERE faculty_id = %s
        """,
        (faculty_id,)
    ).fetchone()

    conn.close()


    # Faculty not found
    if not faculty:

        return jsonify({
            "success": False,
            "message": "Faculty not found"
        }), 404


    # No PPT
    if not faculty["ppt_filename"]:

        return jsonify({
            "success": False,
            "message": "No presentation uploaded"
        }), 404


    # Return faculty information
    return jsonify({

        "success": True,

        "faculty_id":
            faculty["faculty_id"],

        "faculty_name":
            faculty["faculty_name"],

        "ppt_filename":
            faculty["ppt_filename"],

        "download_url":
            url_for(
                "download",
                filename=faculty["ppt_filename"],
                _external=True
            )
    })


# --------------------------------------------------
# PPT Download
# --------------------------------------------------

@app.route("/download/<filename>")
def download(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename,
        as_attachment=True
    )


# --------------------------------------------------
# Initialize PostgreSQL
# --------------------------------------------------

init_database()


# --------------------------------------------------
# Start Server
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
