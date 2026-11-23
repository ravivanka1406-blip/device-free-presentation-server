from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, jsonify, abort)
from werkzeug.utils import secure_filename
import sqlite3
import os
import re
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise RuntimeError('SECRET_KEY environment variable is not configured.')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'database.db'))
ALLOWED_EXTENSIONS = {'ppt', 'pptx'}
FACULTY_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,40}$')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def allowed_file(filename):
    return bool(filename) and '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_faculty_id(value):
    value = value.strip().upper()
    return value if FACULTY_ID_PATTERN.fullmatch(value) else None


def faculty_directory(faculty_id):
    return os.path.join(UPLOAD_FOLDER, faculty_id)


def init_database():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT UNIQUE NOT NULL,
            faculty_name TEXT NOT NULL,
            ppt_filename TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS presentations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE,
            UNIQUE(faculty_id, original_filename),
            UNIQUE(faculty_id, stored_filename)
        )''')
        # Legacy migration: preserve the old upload and register it once.
        old_rows = conn.execute('''SELECT faculty_id, ppt_filename FROM faculty
                                   WHERE ppt_filename IS NOT NULL AND ppt_filename != '' ''').fetchall()
        for row in old_rows:
            fid = row['faculty_id']
            old_name = row['ppt_filename']
            if not clean_faculty_id(fid) or not allowed_file(old_name):
                continue
            old_path = os.path.join(UPLOAD_FOLDER, old_name)
            if not os.path.isfile(old_path):
                continue
            target_dir = faculty_directory(fid)
            os.makedirs(target_dir, exist_ok=True)
            new_name = f'{uuid.uuid4().hex}.{old_name.rsplit(".", 1)[1].lower()}'
            target_path = os.path.join(target_dir, new_name)
            # Move legacy file once. If the process stops, the old DB field remains
            # and a subsequent startup can retry if the source still exists.
            os.replace(old_path, target_path)
            try:
                conn.execute('''INSERT OR IGNORE INTO presentations
                                (faculty_id, original_filename, stored_filename)
                                VALUES (?, ?, ?)''', (fid, old_name, new_name))
                conn.execute('UPDATE faculty SET ppt_filename = NULL WHERE faculty_id = ?', (fid,))
                conn.commit()
            except Exception:
                os.replace(target_path, old_path)
                raise


@app.route('/')
def home():
    with get_db() as conn:
        faculty = conn.execute('''SELECT faculty_id, faculty_name FROM faculty
                                  ORDER BY faculty_id''').fetchall()
        presentations = conn.execute('''SELECT id, faculty_id, original_filename, uploaded_at
                                        FROM presentations ORDER BY faculty_id, original_filename''').fetchall()
    grouped = {}
    for presentation in presentations:
        grouped.setdefault(presentation['faculty_id'], []).append(presentation)
    return render_template('upload.html', faculty=faculty, grouped=grouped)


@app.route('/upload', methods=['POST'])
def upload():
    faculty_id = clean_faculty_id(request.form.get('faculty_id', ''))
    faculty_name = request.form.get('faculty_name', '').strip()
    files = request.files.getlist('presentations')
    if not faculty_id or not faculty_name:
        flash('Valid faculty ID and faculty name are required.')
        return redirect(url_for('home'))
    if not files or any(not f.filename or not allowed_file(f.filename) for f in files):
        flash('Please select only .ppt or .pptx files.')
        return redirect(url_for('home'))
    # Avoid ambiguous duplicate names in the same request.
    names = [secure_filename(f.filename) for f in files]
    if any(not name for name in names) or len(names) != len(set(names)):
        flash('Each uploaded file must have a unique, valid filename.')
        return redirect(url_for('home'))
    target_dir = faculty_directory(faculty_id)
    os.makedirs(target_dir, exist_ok=True)
    saved_paths = []
    old_paths = []
    conn = get_db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('''INSERT INTO faculty (faculty_id, faculty_name) VALUES (?, ?)
                        ON CONFLICT(faculty_id) DO UPDATE SET faculty_name=excluded.faculty_name''',
                     (faculty_id, faculty_name))
        for file, original_name in zip(files, names):
            ext = original_name.rsplit('.', 1)[1].lower()
            stored_name = f'{uuid.uuid4().hex}.{ext}'
            path = os.path.join(target_dir, stored_name)
            file.save(path)
            saved_paths.append(path)
            old = conn.execute('''SELECT stored_filename FROM presentations
                                  WHERE faculty_id = ? AND original_filename = ?''',
                               (faculty_id, original_name)).fetchone()
            if old:
                old_paths.append(os.path.join(target_dir, old['stored_filename']))
                conn.execute('''UPDATE presentations SET stored_filename = ?, uploaded_at = CURRENT_TIMESTAMP
                                WHERE faculty_id = ? AND original_filename = ?''',
                             (stored_name, faculty_id, original_name))
            else:
                conn.execute('''INSERT INTO presentations (faculty_id, original_filename, stored_filename)
                                VALUES (?, ?, ?)''', (faculty_id, original_name, stored_name))
        conn.commit()
    except (sqlite3.Error, OSError):
        conn.rollback()
        for path in saved_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        app.logger.exception('Upload failed')
        flash('Upload failed. No database changes were saved.')
        return redirect(url_for('home'))
    finally:
        conn.close()
    for path in old_paths:
        try:
            os.remove(path)
        except OSError:
            app.logger.exception('Could not remove replaced presentation')
    flash(f'{len(files)} presentation(s) uploaded successfully for {faculty_id}.')
    return redirect(url_for('home'))


@app.route('/delete/<int:presentation_id>', methods=['POST'])
def delete_presentation(presentation_id):
    with get_db() as conn:
        row = conn.execute('''SELECT faculty_id, stored_filename FROM presentations
                              WHERE id = ?''', (presentation_id,)).fetchone()
        if not row:
            abort(404)
        conn.execute('DELETE FROM presentations WHERE id = ?', (presentation_id,))
    try:
        os.remove(os.path.join(faculty_directory(row['faculty_id']), row['stored_filename']))
    except FileNotFoundError:
        pass
    except OSError:
        app.logger.exception('Failed to remove deleted presentation file')
    flash('Presentation deleted.')
    return redirect(url_for('home'))


@app.route('/api/faculty/<faculty_id>')
def faculty_api(faculty_id):
    faculty_id = clean_faculty_id(faculty_id)
    if not faculty_id:
        return jsonify(success=False, message='Invalid faculty ID'), 400
    with get_db() as conn:
        faculty = conn.execute('''SELECT faculty_id, faculty_name FROM faculty
                                  WHERE faculty_id = ?''', (faculty_id,)).fetchone()
        if not faculty:
            return jsonify(success=False, message='Faculty not found'), 404
        rows = conn.execute('''SELECT id, original_filename FROM presentations
                               WHERE faculty_id = ? ORDER BY original_filename''',
                            (faculty_id,)).fetchall()
    return jsonify(success=True, faculty_id=faculty['faculty_id'],
                   faculty_name=faculty['faculty_name'],
                   presentations=[{'id': row['id'], 'filename': row['original_filename'],
                                   'download_url': url_for('download_presentation',
                                                           presentation_id=row['id'], _external=True)}
                                  for row in rows])


@app.route('/download/presentation/<int:presentation_id>')
def download_presentation(presentation_id):
    with get_db() as conn:
        row = conn.execute('''SELECT faculty_id, original_filename, stored_filename
                              FROM presentations WHERE id = ?''', (presentation_id,)).fetchone()
    if not row:
        abort(404)
    return send_from_directory(faculty_directory(row['faculty_id']), row['stored_filename'],
                               as_attachment=True, download_name=row['original_filename'])


@app.errorhandler(413)
def file_too_large(error):
    return 'Request too large. Maximum total upload size is 100 MB.', 413


init_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
