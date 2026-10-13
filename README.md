# Device-Free Presentation System — Server

## Overview

This repository contains the backend server for the Device-Free Presentation System. Developed using Python Flask and SQLite, the application provides a web interface for uploading PowerPoint presentations, managing faculty records, retrieving presentation details through a REST API, and downloading presentation files.

## Features

- Upload PowerPoint presentations in `.ppt` and `.pptx` formats.
- Register faculty members using a unique faculty ID and faculty name.
- Update existing faculty records and their associated presentations.
- Store faculty information and presentation filenames in an SQLite database.
- Retrieve faculty and presentation details in JSON format.
- Generate download URLs for uploaded presentations.
- Download PowerPoint files through a dedicated endpoint.
- Display faculty records through a web interface.

## Technology Stack

- **Programming Language:** Python
- **Backend Framework:** Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, and Jinja2
- **File Handling:** Werkzeug
- **Deployment Platform:** Render
- **Production Server:** Gunicorn

## Project Structure

```text
device-free-presentation-server/
├── static/
│   └── style.css
├── templates/
│   └── upload.html
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

### File Descriptions

- `app.py` — Implements the Flask application, database operations, file uploads, API endpoints, and presentation downloads.
- `templates/upload.html` — Provides the HTML template for the presentation upload interface and faculty records.
- `static/style.css` — Contains the styles for the web interface.
- `requirements.txt` — Lists the Python dependencies required to run the application.
- `.gitignore` — Specifies files and directories excluded from Git.
- `README.md` — Contains project documentation and setup instructions.

The SQLite database and uploaded presentation files are created or populated at runtime.

## Installation and Setup

### Prerequisites

- Python 3
- pip
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/ravivanka1406-blip/device-free-presentation-server.git
cd device-free-presentation-server
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate the environment on Linux or macOS:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file should include:

```text
Flask
gunicorn
```

### 4. Run the Application

Start the development server:

```bash
python app.py
```

The application listens on port `5000`.

Open the following address in your browser:

```text
http://127.0.0.1:5000/
```

The application initializes the SQLite database and creates the upload directory automatically.

## Web Interface

The home page is available at `/`.

It displays the registered faculty records and provides a form for uploading presentations.

The upload form accepts:

- Faculty ID
- Faculty name
- PowerPoint presentation file

When a new faculty ID is submitted, the application creates a faculty record and associates the uploaded file with it. When an existing faculty ID is submitted, the application updates the faculty name and associated presentation.

The current implementation validates uploaded files using their filename extensions and accepts `.ppt` and `.pptx` files.

## API Documentation

### Retrieve Faculty Presentation Details

**Endpoint**

```http
GET /api/faculty/<faculty_id>
```

**Example request**

```http
GET /api/faculty/FAC001
```

**Successful response — HTTP 200**

```json
{
  "success": true,
  "faculty_id": "FAC001",
  "faculty_name": "Example Faculty",
  "ppt_filename": "presentation.pptx",
  "download_url": "https://your-server-url/download/presentation.pptx"
}
```

The example values are illustrative. The actual response contains the faculty details stored in the database.

**Faculty not found — HTTP 404**

```json
{
  "success": false,
  "message": "Faculty not found"
}
```

**No presentation uploaded — HTTP 404**

```json
{
  "success": false,
  "message": "No presentation uploaded"
}
```

### Download a Presentation

**Endpoint**

```http
GET /download/<filename>
```

**Example request**

```http
GET /download/presentation.pptx
```

The endpoint serves the requested file from the upload directory as a downloadable attachment.

## Database

The application uses SQLite to store faculty records.

The `faculty` table contains the following fields:

| Field | Description |
|---|---|
| `id` | Auto-incrementing primary key |
| `faculty_id` | Unique faculty identifier |
| `faculty_name` | Faculty member's name |
| `ppt_filename` | Associated presentation filename |

The table is created automatically if it does not already exist.

## Deployment on Render

The application can be deployed as a Python web service on Render.

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```

The start command assumes that `app.py` contains a Flask application instance named `app`.

After deployment, the service URL can be used to access the web interface and API endpoints.

### Storage Considerations

The application currently stores its SQLite database in `database.db` and uploaded files in the `uploads/` directory.

On hosting platforms, local files may not persist across redeployments or instance replacements. Configure persistent storage or an appropriate managed database and file storage solution when data retention is required.

## Security Considerations

- Keep secret keys and sensitive configuration out of source control.
- Use environment variables for deployment-specific secrets.
- Disable Flask debug mode in production.
- Configure appropriate upload size limits and file validation.
- Implement authentication and authorization for upload and update operations before production use.
- Use HTTPS for public deployments.
- Back up important database records and uploaded files.

## License

No license is currently specified. 
