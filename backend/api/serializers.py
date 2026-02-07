from rest_framework import serializers
from .models import Department, Subject, Teacher, ClassSession, LeaveRequest, SubstitutionProposal
from django.contrib.auth.models import User

# --- BASIC SERIALIZERS ---

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

# --- NESTED SERIALIZERS (For Rich Data) ---

class TeacherSerializer(serializers.ModelSerializer):
    # We nest the User data so we get "First Name" inside the Teacher object
    user = UserSerializer(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'department', 'department_name', 'subjects', 'is_hod', 'fcm_token']

class ClassSessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = ClassSession
        fields = ['id', 'day', 'start_time', 'end_time', 'room_number', 
                  'subject', 'subject_name', 'teacher', 'teacher_name']

class LeaveRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.user.get_full_name', read_only=True)
    final_substitute_name = serializers.CharField(source='final_substitute.user.get_full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'date', 'time_slot', 'reason', 'status', 
                  'requester', 'requester_name', 
                  'final_substitute', 'final_substitute_name', 'created_at']