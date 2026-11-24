# TeamUp — Student Project Collaboration Platform

TeamUp is a multi-page student collaboration website. This completed version adds a FastAPI backend and a SQLite database. It supports registration/login, student profiles, project creation and discovery, project join requests, and student connection requests.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- Internet connection for the first installation (to install Python packages)

## Run locally (Windows PowerShell)

1. Extract `TeamUp_Complete.zip`.
2. Open PowerShell in the extracted `TeamUp_completed` folder (the folder containing `requirements.txt`).
3. Create a virtual environment:

```powershell
py -m venv .venv
```

4. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in the same terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

5. Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

6. Start the backend and website:

```powershell
uvicorn app.main:app --reload
```

7. Open **http://127.0.0.1:8000** in your browser. Do not open the HTML files directly and do not use VS Code Live Server: the FastAPI server serves both the frontend and API.

API documentation is at **http://127.0.0.1:8000/docs** and health check is **http://127.0.0.1:8000/api/health**.

## Database

The app automatically creates `teamup.db` in the project folder on first start. SQLite stores accounts, profiles, projects, join requests, and connections. Passwords are stored as salted PBKDF2 hashes, not plain text.

To reset the local database, stop the server and delete `teamup.db`. This permanently deletes all locally stored accounts and project data.

## Deploy to Render

The included `render.yaml` configures a Render web service and a persistent disk mounted at `/var/data`. A persistent disk is important because SQLite is a file-based database; without persistent storage, data may be lost during redeploys/restarts. The blueprint uses Render's Starter web service plan because persistent disks are not available on the free web-service tier.

1. Create a GitHub account if you do not already have one.
2. Create a new GitHub repository.
3. Extract this ZIP, then upload the **contents** of the `TeamUp_completed` folder to the repository (so `requirements.txt`, `render.yaml`, `app/`, and `frontend/` are at the repository root).
4. Commit and push the files.
5. Sign in to Render, choose **New + → Blueprint**, and connect the GitHub repository.
6. Render detects `render.yaml`. Review the service and persistent disk, then deploy.
7. Wait for the deployment to finish. Open the generated `https://...onrender.com` URL.
8. Keep the generated `SECRET_KEY` private. Render generates it from the blueprint.

### Alternative hosting

You can run the same app on a VPS or any Python host that supports persistent disk storage. Set `SECRET_KEY` to a long random secret, set `DATABASE_PATH` to a writable persistent location, install requirements, then run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For a production deployment with multiple server instances, use PostgreSQL rather than SQLite and configure HTTPS, backups, and an appropriate database connection string.

## Main features

- Register and log in with email and password
- Authenticated pages for projects, teams, profiles, students, and connections
- Create projects with team size and required skills
- Search projects by text and filter by skill
- View project details and submit a join request
- Project owners can accept or reject join requests
- Create/update student profiles and browse other student profiles
- Send, accept, and reject student connection requests

## Project structure

```text
TeamUp_completed/
├── app/
│   └── main.py           # FastAPI routes, authentication, and database setup
├── frontend/             # Website pages, styles, and JavaScript
│   ├── index.html        # Home page
│   ├── login.html        # Register and login
│   ├── project.html      # Create and browse projects
│   ├── details.html      # Project details and join request
│   ├── profile.html      # Student profile
│   ├── students.html     # Student directory
│   ├── teams.html        # Created projects and join requests
│   ├── myprojects.html   # My projects
│   ├── connections.html  # Student connections
│   ├── script.js         # Frontend/API integration
│   └── styles.css
├── requirements.txt
└── render.yaml
```

## Notes

- This project is intended as a student project/demo. Before public production use, add email verification, password reset, rate limiting, automated backups, and stronger operational monitoring.
- Users need to register and log in before using the project, profile, student, team, and connection features.
