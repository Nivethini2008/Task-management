# Task Management Web Application

A beginner-friendly full-stack Task Management Application built with:

- Python Flask
- SQLite
- Flask-SQLAlchemy
- HTML/CSS/JavaScript
- REST API
- Flask-SocketIO for real-time updates
- Password hashing and session authentication
- Responsive web design

## Features

1. User registration and login
2. Secure password hashing
3. User authentication using Flask sessions
4. Create tasks
5. Read/list tasks
6. Update tasks
7. Delete tasks
8. Task status: Pending, In Progress, Completed
9. Priority: Low, Medium, High
10. Due date
11. Search tasks
12. Filter by status and priority
13. Dashboard statistics
14. Real-time task updates using WebSockets
15. Responsive design for desktop and mobile

## Folder structure

```text
task_management_application/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
│
└── static/
    ├── style.css
    └── app.js
```

## How to run on Windows

Open Command Prompt or PowerShell inside this folder.

### 1. Create a virtual environment

```powershell
python -m venv venv
```

### 2. Activate it

PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
venv\Scripts\activate
```

### 3. Install packages

```powershell
pip install -r requirements.txt
```

### 4. Run the application

```powershell
python app.py
```

### 5. Open in Chrome

```text
http://127.0.0.1:5000
```

The SQLite database `tasks.db` is created automatically.

## API endpoints

GET `/api/tasks`
- Returns the logged-in user's tasks.

POST `/api/tasks`
- Creates a task.

PUT `/api/tasks/<id>`
- Updates a task.

DELETE `/api/tasks/<id>`
- Deletes a task.

All task API routes require login.

## Important

Before deploying publicly, change `SECRET_KEY` in `app.py` to a long random secret and use HTTPS.
