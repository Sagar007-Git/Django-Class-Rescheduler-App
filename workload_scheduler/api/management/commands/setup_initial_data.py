"""
Script to set up initial data for the ECE department pilot phase.
Run this after migrations: python manage.py setup_initial_data
"""
import os
import django
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Department, Teacher, Subject, TeacherSubject, ClassSession

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup initial data for ECE department pilot phase'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Setting up initial data...'))

        # 1. Create ECE Department
        ece_dept, created = Department.objects.get_or_create(
            name='Electronics & Communication',
            code='ECE'
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created department: {ece_dept}'))
        else:
            self.stdout.write(self.style.WARNING(f'Department already exists: {ece_dept}'))

        # 2. Create HOD User and Teacher
        hod_user, hod_created = User.objects.get_or_create(
            username='hod_ece',
            defaults={
                'email': 'hod.ece@college.edu',
                'first_name': 'Department',
                'last_name': 'Head',
                'is_hod': True,
                'is_teacher': True,
                'is_staff': True,
            }
        )
        if hod_created:
            hod_user.set_password('hod123')
            hod_user.save()
            self.stdout.write(self.style.SUCCESS('Created HOD user'))
        else:
            self.stdout.write(self.style.WARNING('HOD user already exists'))

        hod_teacher, hod_teacher_created = Teacher.objects.get_or_create(
            user=hod_user,
            defaults={
                'department': ece_dept,
                'full_name': 'Dr. Department Head',
                'employee_id': 'ECE001',
            }
        )
        if hod_teacher_created:
            self.stdout.write(self.style.SUCCESS('Created HOD teacher profile'))
        else:
            self.stdout.write(self.style.WARNING('HOD teacher profile already exists'))

        # 3. Create Sample Teachers
        sample_teachers = [
            {
                'username': 'teacher1',
                'email': 'teacher1@college.edu',
                'first_name': 'John',
                'last_name': 'Smith',
                'employee_id': 'ECE101',
                'full_name': 'Prof. John Smith',
            },
            {
                'username': 'teacher2',
                'email': 'teacher2@college.edu',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'employee_id': 'ECE102',
                'full_name': 'Dr. Sarah Johnson',
            },
            {
                'username': 'teacher3',
                'email': 'teacher3@college.edu',
                'first_name': 'Robert',
                'last_name': 'Williams',
                'employee_id': 'ECE103',
                'full_name': 'Prof. Robert Williams',
            },
            {
                'username': 'teacher4',
                'email': 'teacher4@college.edu',
                'first_name': 'Priya',
                'last_name': 'Patel',
                'employee_id': 'ECE104',
                'full_name': 'Dr. Priya Patel',
            },
        ]

        for teacher_data in sample_teachers:
            user, user_created = User.objects.get_or_create(
                username=teacher_data['username'],
                defaults={
                    'email': teacher_data['email'],
                    'first_name': teacher_data['first_name'],
                    'last_name': teacher_data['last_name'],
                    'is_teacher': True,
                }
            )
            if user_created:
                user.set_password('teacher123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {teacher_data["username"]}'))

            teacher, teacher_created = Teacher.objects.get_or_create(
                user=user,
                defaults={
                    'department': ece_dept,
                    'full_name': teacher_data['full_name'],
                    'employee_id': teacher_data['employee_id'],
                }
            )
            if teacher_created:
                self.stdout.write(self.style.SUCCESS(f'Created teacher: {teacher_data["full_name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Teacher already exists: {teacher_data["full_name"]}'))

        # 4. Create Sample Subjects for ECE Department
        sample_subjects = [
            {'code': 'EC301', 'name': 'Digital Electronics'},
            {'code': 'EC302', 'name': 'Signals and Systems'},
            {'code': 'EC303', 'name': 'Electronic Circuits'},
            {'code': 'EC501', 'name': 'Communication Systems'},
            {'code': 'EC502', 'name': 'Microprocessors'},
            {'code': 'EC503', 'name': 'Control Systems'},
            {'code': 'EC701', 'name': 'VLSI Design'},
            {'code': 'EC702', 'name': 'Wireless Communication'},
            {'code': 'EC703', 'name': 'Embedded Systems'},
        ]

        for subj_data in sample_subjects:
            subject, created = Subject.objects.get_or_create(
                code=subj_data['code'],
                department=ece_dept,
                defaults={'name': subj_data['name']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subject: {subj_data["code"]} - {subj_data["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Subject already exists: {subj_data["code"]}'))

        # 5. Assign subjects to teachers
        teachers = Teacher.objects.filter(department=ece_dept).exclude(id=hod_teacher.id)
        subjects = Subject.objects.filter(department=ece_dept)

        # Each teacher gets 3-4 subjects they're qualified to teach
        teacher_subject_assignments = {}
        for i, teacher in enumerate(teachers):
            # Assign subjects based on index for variety
            start_idx = i * 2 % len(subjects)
            teacher_subjects = subjects[start_idx:start_idx + 4]
            teacher_subject_assignments[teacher] = teacher_subjects

        for teacher, qualified_subjects in teacher_subject_assignments.items():
            for subject in qualified_subjects:
                ts, created = TeacherSubject.objects.get_or_create(
                    teacher=teacher,
                    subject=subject
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Assigned {subject.code} to {teacher.full_name}'))

        # 6. Create Sample Class Sessions (Timetable)
        from datetime import time

        sample_sessions = [
            # Monday
            {'day': 0, 'start': time(9, 0), 'end': time(10, 0), 'semester': 3, 'section': 'A', 'subject_code': 'EC301'},
            {'day': 0, 'start': time(10, 0), 'end': time(11, 0), 'semester': 5, 'section': 'A', 'subject_code': 'EC501'},
            {'day': 0, 'start': time(11, 0), 'end': time(12, 0), 'semester': 7, 'section': 'A', 'subject_code': 'EC701'},
            {'day': 0, 'start': time(14, 0), 'end': time(15, 0), 'semester': 3, 'section': 'B', 'subject_code': 'EC301'},
            
            # Tuesday (Variable schedule example)
            {'day': 1, 'start': time(8, 0), 'end': time(9, 0), 'semester': 3, 'section': 'A', 'subject_code': 'EC302'},
            {'day': 1, 'start': time(9, 0), 'end': time(10, 0), 'semester': 3, 'section': 'A', 'subject_code': 'EC303'},
            {'day': 1, 'start': time(10, 0), 'end': time(11, 0), 'semester': 3, 'section': 'A', 'subject_code': 'EC302'},
            {'day': 1, 'start': time(11, 0), 'end': time(12, 0), 'semester': 5, 'section': 'A', 'subject_code': 'EC502'},
            {'day': 1, 'start': time(12, 0), 'end': time(13, 0), 'semester': 5, 'section': 'A', 'subject_code': 'EC503'},
            {'day': 1, 'start': time(14, 0), 'end': time(15, 0), 'semester': 7, 'section': 'A', 'subject_code': 'EC702'},
            {'day': 1, 'start': time(15, 0), 'end': time(16, 0), 'semester': 7, 'section': 'A', 'subject_code': 'EC703'},
            
            # Wednesday
            {'day': 2, 'start': time(9, 0), 'end': time(10, 30), 'semester': 3, 'section': 'A', 'subject_code': 'EC303'},
            {'day': 2, 'start': time(11, 0), 'end': time(12, 30), 'semester': 5, 'section': 'B', 'subject_code': 'EC501'},
        ]

        teachers_list = list(teachers)
        
        for i, session_data in enumerate(sample_sessions):
            try:
                subject = Subject.objects.get(
                    code=session_data['subject_code'],
                    department=ece_dept
                )
                
                # Assign teacher who is qualified for this subject
                qualified_teachers = Teacher.objects.filter(
                    qualified_subjects__subject=subject
                )
                
                if qualified_teachers.exists():
                    assigned_teacher = qualified_teachers.first()
                else:
                    # If no teacher qualified, assign a random teacher
                    assigned_teacher = teachers_list[i % len(teachers_list)]
                
                session, created = ClassSession.objects.get_or_create(
                    day_of_week=session_data['day'],
                    start_time=session_data['start'],
                    end_time=session_data['end'],
                    semester=session_data['semester'],
                    section=session_data['section'],
                    defaults={
                        'subject': subject,
                        'assigned_teacher': assigned_teacher,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f'Created class session: {session}'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'Class session already exists: {session}'
                    ))
                    
            except Subject.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Subject not found: {session_data["subject_code"]}'
                ))

        self.stdout.write(self.style.SUCCESS('Initial data setup completed!'))
        self.stdout.write(self.style.SUCCESS('\nSample Login Credentials:'))
        self.stdout.write(self.style.SUCCESS('HOD: username=hod_ece, password=hod123'))
        self.stdout.write(self.style.SUCCESS('Teachers: username=teacher1, password=teacher123'))
        self.stdout.write(self.style.SUCCESS('               teacher2, teacher3, teacher4'))