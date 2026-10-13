# Device-Free Presentation System — Server

## Overview

This repository contains the backend server for the Device-Free Presentation System. The application is developed using Python Flask and SQLite to manage faculty information and PowerPoint presentation files.

The server provides a web interface for uploading presentations, maintains faculty records, exposes an API for retrieving presentation details, and provides an endpoint for downloading uploaded files.

## Features

- Upload PowerPoint presentations in `.ppt` and `.pptx` formats.
- Register faculty members using a unique faculty ID and faculty name.
- Update the presentation associated with an existing faculty ID.
- Store faculty information and presentation filenames in an SQLite database.
- Retrieve faculty and presentation details in JSON format through a REST API.
- Generate download URLs for stored presentations.
- Download PowerPoint files through a dedicated endpoint.
- Display faculty records through a web interface.

## Technology Stack

- **Programming Language:** Python
- **Backend Framework:** Flask
- **Database:** SQLite
- **Frontend Templating:** HTML and Jinja2
- **File Handling:** Werkzeug
- **Deployment Platform:** Render
- **Production WSGI Server:** Gunicorn

## Project Structure

```text
device-free-presentation-server/
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
├── templates/
│   └── upload.html
└── uploads/
```

The `uploads/` directory is created automatically when the application starts. The SQLite database is also initialized automatically.

## Installation and Setup

### Prerequisites

- Python 3
- pip
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the repository URL with the URL of this repository.

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

Create a `requirements.txt` file with the following dependencies:

```text
Flask
gunicorn
```

Install them using:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

The development server listens on port `5000`.

Open the following address in your browser:

```text
http://127.0.0.1:5000/
```

The application initializes the SQLite database and creates the upload directory when it starts.

## Web Interface

The home page (`/`) displays existing faculty records and provides the presentation upload interface.

The upload form accepts a faculty ID, faculty name, and PowerPoint file.

When a new faculty ID is submitted, the application creates a faculty record and associates the uploaded presentation with it. When an existing faculty ID is submitted, the application updates the faculty name and associated presentation.

Only files with `.ppt` and `.pptx` extensions are accepted by the current file-extension validation.

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

The response includes the faculty identifier, faculty name, presentation filename, and a generated download URL. The values above are examples.

**Faculty not found — HTTP 404**

```json
{
  "success": false,
  "message": "Faculty not found"
}
```

**No presentation associated with the faculty record — HTTP 404**

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

The endpoint serves the requested file from the configured upload directory as a downloadable attachment.

## Database

The application uses SQLite to store faculty information.

The `faculty` table contains the following fields:

| Field | Description |
|---|---|
| `id` | Auto-incrementing primary key |
| `faculty_id` | Unique faculty identifier |
| `faculty_name` | Faculty member's name |
| `ppt_filename` | Associated presentation filename |

The database table is created automatically if it does not already exist.

## Deployment

The application can be deployed as a Python web service on Render.

**Build command**

```bash
pip install -r requirements.txt
```

**Start command**

```bash
gunicorn app:app
```

The start command assumes that the Flask application instance is named `app` in `app.py`.

After deployment, the service URL can be used to access the web interface and API endpoints.

### Storage

The application stores uploaded files in the `uploads/` directory and database records in `database.db`.

When deploying to a hosting platform, configure persistent storage if uploaded files and database records must survive redeployments or instance replacements. The current implementation uses local SQLite storage and local file storage.

## Security

- Keep secret keys and other sensitive configuration out of source control.
- Use environment variables for deployment-specific secrets.
- Disable Flask debug mode in production.
- Configure appropriate file upload size limits and file validation.
- Restrict upload and update operations with authentication and authorization before production use.
- Use HTTPS for public deployments.
- Back up important database records and uploaded files.

## License

No license is specified.
