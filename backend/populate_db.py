import os
import django
import random
from datetime import time, date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Department, Subject, Teacher, ClassSession, LeaveRequest

# --- CONFIGURATION ---
DEPT_NAME = "Electronics & Communication"
DEPT_CODE = "ECE"

TEACHER_NAMES = [
    ("Aarav", "Sharma"),      # Teacher 1
    ("Vivaan", "Gupta"),      # Teacher 2
    ("Aditya", "Iyer"),       # Teacher 3
    ("Vihaan", "Malhotra"),   # Teacher 4
    ("Arjun", "Singh"),       # Teacher 5
    ("Amit", "Verma"),        # Teacher 6 (Busy Scenario)
    ("Sneha", "Reddy"),       # Teacher 7 (High Load Scenario)
    ("Sagar", "Patil"),       # Teacher 8 (YOU - The Hero)
    ("Reyansh", "Kaur"),      # Teacher 9
    ("Muhammad", "Khan"),     # Teacher 10
    ("Krishna", "Das"),       # Teacher 11
    ("Ananya", "Nair"),       # Teacher 12
    ("Diya", "Menon"),        # Teacher 13
    ("Kavya", "Joshi"),       # Teacher 14
    ("Suresh", "Rao")         # Teacher 15 (HOD)
]

# ECE Subjects with Semesters
SUBJECTS_DATA = [
    # Sem 3
    {"name": "Digital Electronics", "code": "EC301", "sem": 3},
    {"name": "Signals and Systems", "code": "EC302", "sem": 3},
    {"name": "Network Theory", "code": "EC303", "sem": 3},
    # Sem 5
    {"name": "Microprocessors", "code": "EC501", "sem": 5},
    {"name": "Control Systems", "code": "EC502", "sem": 5},
    {"name": "DSP", "code": "EC503", "sem": 5},
    # Sem 7
    {"name": "VLSI Design", "code": "EC701", "sem": 7},
    {"name": "Embedded Systems", "code": "EC702", "sem": 7},
    {"name": "Wireless Comm", "code": "EC703", "sem": 7},
]

# Time Slots (Mon-Fri, 9 AM - 4 PM)
DAYS = [0, 1, 2, 3, 4] # Mon=0, Fri=4
TIMES = [time(9,0), time(10,0), time(11,0), time(12,0), time(14,0), time(15,0)]

def populate():
    print(f"--- STARTING POPULATION FOR {DEPT_CODE} ---")
    confirm = input("This will WIPE all data. Type 'yes' to proceed: ")
    if confirm != 'yes': return

    # 1. WIPE DATA
    print("1. Wiping Database...")
    LeaveRequest.objects.all().delete()
    ClassSession.objects.all().delete()
    Teacher.objects.all().delete()
    Subject.objects.all().delete()
    Department.objects.all().delete()
    User.objects.filter(username__startswith="teacher").delete()

    # 2. CREATE DEPT & SUBJECTS
    print(f"2. Creating {DEPT_NAME}...")
    dept = Department.objects.create(name=DEPT_NAME, code=DEPT_CODE)
    
    db_subjects = []
    for sub in SUBJECTS_DATA:
        s = Subject.objects.create(name=sub["name"], code=sub["code"], department=dept)
        db_subjects.append(s)
        print(f"   - Created: {sub['name']} (Sem {sub['sem']})")

    # 3. CREATE TEACHERS
    print("3. Creating 15 Teachers...")
    teachers = []
    
    for i, (first, last) in enumerate(TEACHER_NAMES, start=1):
        username = f"teacher{i}"
        
        # Create User
        u = User.objects.create_user(
            username=username, 
            password="password123",
            first_name=first,
            last_name=last,
            email=f"{first.lower()}.{last.lower()}@college.edu"
        )
        
        # Determine Role & Mobile
        is_hod = (i == 15)
        mobile = f"+9198765432{i:02d}"
        if i == 8: mobile = "+917019162285" # YOUR NUMBER
        
        t = Teacher.objects.create(user=u, department=dept, is_hod=is_hod, mobile_number=mobile)
        teachers.append(t)

        # Assign Skills (3 subjects each)
        # Using simple modulo logic to distribute subjects evenly
        my_subs = [db_subjects[i % len(db_subjects)], db_subjects[(i+1) % len(db_subjects)]]
        t.subjects.set(my_subs)
        t.save()
        print(f"   - {first} {last} ({username}) -> {my_subs[0].name}, {my_subs[1].name}")

    # 4. GENERATE FULL SCHEDULE (The Heavy Lifting)
    print("\n4. Generating Weekly Schedule (Randomized)...")
    total_sessions = 0
    
    for t in teachers:
        # Each teacher gets 4-6 random classes per week
        num_classes = random.randint(4, 6)
        
        # Prevent double booking using a set of (day, time)
        booked_slots = set()
        
        for _ in range(num_classes):
            # Pick Random Day & Time
            d = random.choice(DAYS)
            tm = random.choice(TIMES)
            
            # Avoid duplicate slot for same teacher
            if (d, tm) in booked_slots: continue
            
            # Avoid the "Trap" slot (Wed 11 AM) for Teacher 8 (Sagar) so he is free
            # And avoid Wed 11 AM for Teacher 6 (Amit) so we can manually set him BUSY later
            if d == 2 and tm == time(11,0) and (t.id == teachers[7].id or t.id == teachers[5].id):
                continue

            ClassSession.objects.create(
                teacher=t,
                subject=t.subjects.first(), # Just pick their first subject
                day=d,
                start_time=tm,
                end_time=(datetime.combine(date.today(), tm) + timedelta(hours=1)).time(),
                room_number=f"{random.randint(101, 305)}"
            )
            booked_slots.add((d, tm))
            total_sessions += 1

    print(f"   - Generated {total_sessions} regular class sessions.")

    # 5. SETTING THE TRAP (Specific Scenarios)
    print("\n5. Setting up 'The Perfect Storm' (Wed 11:00 AM)...")
    
    # Target: Wednesday (Day 2) at 11:00 AM
    
    # Scenario A: Teacher 6 (Amit Verma) is BUSY
    ClassSession.objects.create(
        teacher=teachers[5], # Teacher 6
        subject=db_subjects[2], 
        day=2, 
        start_time=time(11, 0), 
        end_time=time(12, 0),
        room_number="LAB-1"
    )
    print("   - Amit Verma (Teacher 6) is manually set to BUSY.")

    # Scenario B: Teacher 7 (Sneha Reddy) is OVERWORKED
    # We give her 3 filled leave requests earlier in the week
    for _ in range(3):
        LeaveRequest.objects.create(
            requester=teachers[0], 
            final_substitute=teachers[6], # Teacher 7
            date=date(2024, 2, 12), # Monday
            time_slot=time(9, 0),
            status='FILLED'
        )
    print("   - Sneha Reddy (Teacher 7) is manually set to TIRED (Load=3).")

    # Scenario C: Teacher 8 (Sagar) is FREE
    # We ensured in step 4 that he has NO class on Wed 11 AM.
    print(f"   - Sagar Patil (Teacher 8) is FREE and READY.")

    print("\n--- DONE! ECE Schedule Complete. ---")

# Helper for time math
from datetime import datetime

if __name__ == '__main__':
    populate()