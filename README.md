# Face Matcher Admin Portal

A modern Flask-based web application for face matching, with a secure admin portal for managing gallery images, Google Drive integration, admin users, and user activity logs. The admin backend uses Supabase for authentication and logging.

---

## Features

- **User Frontend**
  - Upload and match face images.
  - Submit email to receive results.
  - Clean, responsive UI.

- **Admin Portal**
  - Secure login/logout (Supabase-based).
  - Dashboard with glassmorphism UI.
  - Google Drive link upload for gallery images.
  - Upload Google Drive API credentials.
  - Manage gallery images (delete all).
  - Admin management (add, edit, delete admins).
  - View user activity logs (with search/filter).
  - All admin/user actions logged in Supabase.
  - Session management and access control.

---

## Project Structure

```
matam/
├── app.py                  # Main Flask backend
├── templates/
│   ├── index.html          # User-facing frontend
│   ├── admin_dashboard.html# Admin dashboard UI
│   └── admin_login.html    # Admin login page
├── static/
│   ├── styles.css          # Shared styles
│   └── gallery/            # Uploaded gallery images
├── drive_utils.py          # Google Drive integration
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Install Python Dependencies

It’s recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the root directory with the following (fill in your values):

```
SECRET_KEY=your_flask_secret_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_email_password
```

### 4. Supabase Setup

- Create a Supabase project.
- Create the following tables:
  - `admins` (id, username, password_hash, email, created_at)
  - `user_logs` (id, email, ip_address, created_at)
- Set up Row Level Security (RLS) as needed.
- Insert your initial admin user (see code comments in `app.py`).

### 5. Google Drive API

- Place your `credentials.json` in the project root, or upload via the admin dashboard.

---

## Running the App

```bash
python app.py
```

- Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) for the user frontend.
- Visit [http://127.0.0.1:5000/admin/login?show=1](http://127.0.0.1:5000/admin/login?show=1) for the admin portal.

---

## Usage

- **User:** Upload a face image, submit your email, and receive results.
- **Admin:** Log in, manage gallery, upload Drive links/credentials, manage admins, and view user logs.

---

## Security Notes

- All admin authentication and logs are stored in Supabase.
- Passwords are hashed with bcrypt.
- Only admins can access the dashboard and sensitive routes.
- User actions are logged for auditing.
- **IMPORTANT:** You must set a strong, random `SECRET_KEY` in your `.env` file or environment variables. If `SECRET_KEY` is missing, Flask sessions will not be secure and you may see warnings or errors. Example:
  ```
  SECRET_KEY=your-very-strong-random-string
  ```

---

## Customization

- Update styles in `