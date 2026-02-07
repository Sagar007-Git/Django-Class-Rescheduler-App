# Dynamic Teaching Workload Scheduler - Backend API Documentation

## 1. Setup Instructions
To run this backend on your local machine:

1.  **Install Python & MySQL.**
2.  **Create Database:** Create a MySQL database named `scheduler_db`.
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run Migrations:**
    ```bash
    python manage.py migrate
    ```
5.  **Create Admin User:**
    ```bash
    python manage.py createsuperuser
    ```
6.  **Run Server:**
    ```bash
    python manage.py runserver 0.0.0.0:8000
    ```
    * **Base URL:** `http://<YOUR_IP_ADDRESS>:8000/api`
---

## 2. Authentication (Global Rule)
* **Header:** All endpoints (except Login) require the Authorization header.
* **Format:** `Authorization: Token <your_token_string>`

---

## 3. Endpoints

### A. Authentication
* **POST** `/auth/login/` -> `{ "username": "...", "password": "..." }`

### B. Setup (Crucial for Notifications)
* **POST** `/fcm/update/` -> `{ "fcm_token": "device_token_from_firebase" }`
  *(Call this immediately after login so we can send push notifications!)*

### C. User Profile
* **GET** `/profile/` -> Returns Teacher details, Dept, and ID.

### D. Schedule & Calendar
* **GET** `/schedule/weekly/` -> Returns `{ "regular_schedule": [], "upcoming_substitutions": [] }`

### E. Substitution Workflow
1.  **POST** `/substitutes/recommend/` -> `{ "date": "...", "time_slot": "...", "subject_id": 1 }`
    *(Returns list of available teachers sorted by workload)*
2.  **POST** `/requests/create/` -> `{ "date": "...", "time_slot": "...", "preferred_teacher_ids": [1, 2] }`
3.  **POST** `/hod/requests/{id}/action/` -> `{ "action": "APPROVE" }`
    *(Approving triggers the Firebase Push Notification)*
4.  **POST** `/requests/{id}/respond/` -> `{ "action": "ACCEPT" }`
    *(First to accept gets the job)*
    
## 4. Status Codes
* **200 OK:** Success.
* **201 Created:** Successfully created (e.g., new request).
* **400 Bad Request:** Logic error (e.g., "Too late! Another teacher accepted it").
* **403 Forbidden:** Permission denied (e.g., Non-HOD trying to approve).

## 5. Database Setup (Crucial Step)

You do NOT need to create tables manually. Django will create them for you. 
You only need to create the **empty database shell**.

1.  **Open MySQL Workbench** (or your command line).
2.  **Run this SQL command:**
    ```sql
    CREATE DATABASE scheduler_db;
    ```
3.  **That's it.** Now go to your terminal and run:
    ```bash
    python manage.py migrate
    ```
    *(This command magically converts the Python code into the 8 Tables: Teachers, Classes, Requests, etc.)*

4.  **Create the Superuser (Admin):**
    ```bash
    python manage.py createsuperuser
    ```
    *(Follow the prompts to create your login for the Admin Panel).*
