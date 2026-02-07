import os
import django
import random
from datetime import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Department, Subject, Teacher, ClassSession

def populate():
    print("WARNING: This will clear existing data to ensure a clean test.")
    confirm = input("Type 'yes' to proceed: ")
    if confirm != 'yes':
        return

    # 1. Clear Data
    print("Clearing old data...")
    ClassSession.objects.all().delete()
    Teacher.objects.all().delete()
    Subject.objects.all().delete()
    Department.objects.all().delete()
    User.objects.filter(username__startswith="teacher").delete()

    # 2. Create Department
    ece = Department.objects.create(name="Electronics & Comm", code="ECE")
    print(f"Created Dept: {ece}")

    # 3. Create Subjects (Mapped to Semesters)
    # We use the code to hint at the semester (e.g., EC301 = 3rd Sem)
    subjects_data = [
        ("Network Analysis", "EC301"),   # 3rd Sem
        ("Analog Circuits", "EC302"),    # 3rd Sem
        ("Control Systems", "EC501"),    # 5th Sem
        ("VLSI Design", "EC502"),        # 5th Sem
        ("Embedded Systems", "EC701"),   # 7th Sem
        ("Artificial Intel", "EC702")    # 7th Sem
    ]
    
    db_subjects = []
    for name, code in subjects_data:
        sub = Subject.objects.create(name=name, code=code, department=ece)
        db_subjects.append(sub)
        print(f"Created Subject: {name}")

    # 4. Create 10 Teachers
    # We divide them into groups so they have different qualifications
    print("Creating 10 Teachers...")
    
    # Group A: Juniors (Teach 3rd Sem) - Teachers 1-3
    # Group B: Seniors (Teach 5th Sem) - Teachers 4-6
    # Group C: Experts (Teach 7th Sem) - Teachers 7-9
    # Group D: The HOD (Teaches Everything) - Teacher 10

    for i in range(1, 11):
        username = f"teacher{i}"
        user = User.objects.create_user(username=username, password="password123")
        is_hod = (i == 10) # Teacher 10 is HOD
        
        teacher = Teacher.objects.create(user=user, department=ece, is_hod=is_hod)
        
        # Assign Subjects Logic
        if i <= 3:
            # Juniors teach 3rd Sem subjects
            teacher.subjects.add(db_subjects[0], db_subjects[1])
        elif i <= 6:
            # Seniors teach 5th Sem (VLSI, Control)
            teacher.subjects.add(db_subjects[2], db_subjects[3])
        elif i <= 9:
            # Experts teach 7th Sem
            teacher.subjects.add(db_subjects[4], db_subjects[5])
        else:
            # HOD teaches VLSI and AI
            teacher.subjects.add(db_subjects[3], db_subjects[5])
            
        teacher.save()

    print("Teachers Created: teacher1 to teacher10 (Password: password123)")

    # 5. Create a "Monday Morning" Schedule (The Trap)
    # We want to test substitution for Monday 10:00 AM.
    # Let's make HALF of them busy so the algorithm has to work.
    
    target_time = time(10, 0) # 10:00 AM
    monday = 0 # Monday
    
    # Teachers 1, 2, 4, 7, 10 are BUSY teaching at 10 AM.
    # Teachers 3, 5, 6, 8, 9 are FREE.
    
    busy_indices = [1, 2, 4, 7, 10] 
    
    print("Creating Schedule for Monday 10:00 AM...")
    for i in busy_indices:
        t_obj = Teacher.objects.get(user__username=f"teacher{i}")
        # Assign them a random class
        sub = t_obj.subjects.first() 
        ClassSession.objects.create(
            teacher=t_obj,
            subject=sub,
            day=monday,
            start_time=target_time,
            end_time=time(11, 0),
            room_number=f"Room-{100+i}"
        )
        print(f"  -> Teacher{i} is BUSY teaching {sub.name}")

    print("Population Complete! Ready to Test.")

if __name__ == '__main__':
    populate()