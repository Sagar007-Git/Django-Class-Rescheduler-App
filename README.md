# Dynamic Teaching Workload Scheduler - Backend API Documentation

## 1. Setup Instructions
To run this backend on your local machine:

1.  **Install Python & MySQL.**
2.  **Create Database:** Create a MySQL database named `scheduler_db`.
3.  **Configure Database:** Open `backend/settings.py` and update the `DATABASES` section with your MySQL password.
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Run Migrations:**
    ```bash
    python manage.py migrate
    ```
6.  **Create Admin User:**
    ```bash
    python manage.py createsuperuser
    ```
7.  **Run Server:**
    ```bash
    python manage.py runserver 0.0.0.0:8000
    ```
    * **Base URL:** `http://<YOUR_IP_ADDRESS>:8000/api`
    * **Note:** If running on Emulator, use `http://10.0.2.2:8000/api`.

---

## 2. Authentication (Global Rule)
* **Header:** All endpoints (except Login) require the Authorization header.
* **Format:** `Authorization: Token <your_token_string>`

---

## 3. Endpoints

### A. Authentication
#### 1. Login
* **URL:** `/auth/login/`
* **Method:** `POST`
* **Body:**
    ```json
    {
      "username": "DrSmith",
      "password": "password123"
    }
    ```
* **Response:**
    ```json
    { "token": "9f8e7d6c..." }
    ```

### B. User Profile
#### 2. Get User Profile
* **URL:** `/profile/`
* **Method:** `GET`
* **Response:**
    ```json
    {
      "id": 1,
      "user": { "first_name": "John", "last_name": "Smith", "email": "john@example.com" },
      "department_name": "ECE",
      "subjects": [1, 2],
      "is_hod": false,
      "fcm_token": "device_token_xyz"
    }
    ```

### C. Schedule & Calendar
#### 3. Get Weekly Schedule
* **URL:** `/schedule/weekly/`
* **Method:** `GET`
* **Description:** Returns the teacher's static timetable AND any substitution classes they have accepted.
* **Response:**
    ```json
    {
      "regular_schedule": [
        { "day": 0, "start_time": "10:00:00", "subject_name": "VLSI", "room_number": "101" }
      ],
      "upcoming_substitutions": [
        { "id": 5, "date": "2024-02-12", "time_slot": "10:00:00", "status": "FILLED" }
      ]
    }
    ```

### D. Substitution Workflow (The Core Logic)
#### 4. Recommend Substitutes (For Requester)
* **URL:** `/substitutes/recommend/`
* **Method:** `POST`
* **Body:**
    ```json
    {
      "date": "2024-02-12",
      "time_slot": "10:00:00",
      "subject_id": 1
    }
    ```
* **Response:** A list of valid teachers sorted by "Least Workload".
    ```json
    [
      { "id": 5, "user": { "username": "DrLee" }, "total_load": 2 },
      { "id": 8, "user": { "username": "DrDoe" }, "total_load": 5 }
    ]
    ```

#### 5. Create Substitution Request
* **URL:** `/requests/create/`
* **Method:** `POST`
* **Body:**
    ```json
    {
      "date": "2024-02-12",
      "time_slot": "10:00:00",
      "reason": "Medical Leave",
      "preferred_teacher_ids": [5, 8]  // IDs from the recommendation list
    }
    ```

#### 6. Respond to Request (For Substitute)
* **URL:** `/requests/{id}/respond/`
* **Method:** `POST`
* **Body:**
    ```json
    { "action": "ACCEPT" }  // or "REJECT"
    ```
* **Note:** This endpoint uses **Optimistic Locking**. The first person to send "ACCEPT" gets the class.

### E. HOD Administrative Actions
#### 7. Approve/Reject Request
* **URL:** `/hod/requests/{id}/action/`
* **Method:** `POST`
* **Body:**
    ```json
    { "action": "APPROVE" }  // or "REJECT"
    ```
* **Effect:**
    * **APPROVE:** Changes status to `APPROVED_OPEN` and sends Firebase Push Notifications to candidates.
    * **REJECT:** Changes status to `REJECTED`.

---

## 4. Status Codes
* **200 OK:** Success.
* **201 Created:** Successfully created (e.g., new request).
* **400 Bad Request:** Logic error (e.g., "Too late! Another teacher accepted it").
* **403 Forbidden:** Permission denied (e.g., Non-HOD trying to approve).
