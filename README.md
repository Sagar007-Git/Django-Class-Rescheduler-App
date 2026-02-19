# Django Class Rescheduler App

## Introduction

Django Class Rescheduler App is a web-based application built using the Django framework. It allows users to manage and reschedule academic classes efficiently. The application provides interfaces for administrators, faculty, and students to view, request, and manage class schedules and rescheduling requests.

## Features

- User authentication and registration.
- Role-based user access for administrators, faculty, and students.
- Dashboard views tailored to user roles.
- Faculty can request class rescheduling with specific details.
- Administrators can review and approve or reject reschedule requests.
- Students and faculty can view upcoming class schedules.
- Notifications for reschedule requests and their status.
- Responsive user interface for seamless navigation.
- Error handling for invalid requests and authentication failures.

## Requirements

- Python 3.x
- Django (compatible version as specified in the project)
- SQLite (default) or any supported Django database backend
- Django Crispy Forms
- Bootstrap (for frontend styling)
- Other dependencies as listed in `requirements.txt`

## Installation

Follow these steps to set up the Django Class Rescheduler App:

1. **Clone the repository**
   ```bash
   git clone https://github.com/Sagar007-Git/Django-Class-Rescheduler-App.git
   cd Django-Class-Rescheduler-App
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (administrator)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. Access the app in your browser at `http://127.0.0.1:8000/`

## Usage

Once the application is running, you can use it as follows:

- **Registration/Login:** Users can register for a new account or log in using existing credentials.
- **Admin Dashboard:** Administrators can manage users, view all class schedules, and handle reschedule requests.
- **Faculty Dashboard:** Faculty can view their schedules, request rescheduling, and receive notifications about the status of their requests.
- **Student Dashboard:** Students can view their class schedules and receive updates about any rescheduling.
- **Reschedule Requests:** Faculty submit reschedule requests via an intuitive form specifying date, time, and reason. Admins review requests and update statuses accordingly.
- **Notifications:** The system provides feedback and notifications about request statuses and schedule updates.

## Configuration

The application uses Django's standard settings and can be configured as follows:

- **Database:** By default, the app uses SQLite. You can configure other databases in `settings.py`.
- **Static Files:** Configure static files handling in `settings.py` as per your deployment environment.
- **Email Notifications:** Configure email backend in `settings.py` for email notifications (if implemented).
- **User Roles:** The app defines roles for Admin, Faculty, and Student in the user model or via Django's group/permission system.
- **Environment Variables:** Store sensitive settings like secret keys and database credentials in environment variables or a `.env` file.

For advanced configuration, refer to Django's official documentation and modify `settings.py` as needed for your deployment.

---

This README provides an overview of the Django Class Rescheduler App, its features, installation steps, usage, and configuration details. Refer to the source code and in-app documentation for more specific functionality and customization options.