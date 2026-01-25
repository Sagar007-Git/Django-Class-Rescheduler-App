"""
Serializers for the Dynamic Teaching Workload Scheduler API.
"""
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    User, Department, Teacher, Subject, 
    TeacherSubject, ClassSession, LeaveRequest, 
    SubstitutionProposal
)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']
        read_only_fields = ['id']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_hod', 'is_teacher', 'role_display', 'is_active'
        ]
        read_only_fields = ['id', 'role_display']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """Update user with password hashing."""
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class TeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teacher model."""
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='department',
        write_only=True,
        required=True
    )
    email = serializers.EmailField(source='user.email', read_only=True)
    is_hod = serializers.BooleanField(source='user.is_hod', read_only=True)
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'department', 'department_id',
            'full_name', 'employee_id', 'fcm_token',
            'email', 'is_hod'
        ]
        read_only_fields = ['id', 'user', 'email', 'is_hod']


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model."""
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='department',
        write_only=True,
        required=True
    )
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'department', 'department_id']
        read_only_fields = ['id']


class TeacherSubjectSerializer(serializers.ModelSerializer):
    """Serializer for Teacher-Subject qualification relationship."""
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        required=True
    )
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True,
        required=True
    )
    
    class Meta:
        model = TeacherSubject
        fields = ['id', 'teacher', 'teacher_id', 'subject', 'subject_id']
        read_only_fields = ['id']


class ClassSessionSerializer(serializers.ModelSerializer):
    """Serializer for ClassSession model."""
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True,
        required=True
    )
    assigned_teacher = TeacherSerializer(read_only=True)
    assigned_teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='assigned_teacher',
        write_only=True,
        required=True
    )
    day_of_week_display = serializers.CharField(
        source='get_day_of_week_display', 
        read_only=True
    )
    semester_display = serializers.CharField(
        source='get_semester_display', 
        read_only=True
    )
    
    class Meta:
        model = ClassSession
        fields = [
            'id', 'subject', 'subject_id',
            'assigned_teacher', 'assigned_teacher_id',
            'day_of_week', 'day_of_week_display',
            'start_time', 'end_time',
            'semester', 'semester_display',
            'section', 'duration_minutes'
        ]
        read_only_fields = ['id', 'duration_minutes', 'day_of_week_display', 'semester_display']


class WeeklyScheduleSerializer(serializers.Serializer):
    """
    Serializer for weekly schedule view.
    Combines regular sessions and substitutions.
    """
    id = serializers.IntegerField()
    date = serializers.DateField()
    subject = SubjectSerializer()
    assigned_teacher = TeacherSerializer()
    day_of_week = serializers.IntegerField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    semester = serializers.IntegerField()
    section = serializers.CharField()
    is_substitution = serializers.BooleanField()
    substitution_details = serializers.DictField(required=False, allow_null=True)
    
    class Meta:
        fields = [
            'id', 'date', 'subject', 'assigned_teacher',
            'day_of_week', 'start_time', 'end_time',
            'semester', 'section', 'is_substitution',
            'substitution_details'
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model."""
    requester = TeacherSerializer(read_only=True)
    class_session = ClassSessionSerializer(read_only=True)
    class_session_id = serializers.PrimaryKeyRelatedField(
        queryset=ClassSession.objects.all(),
        source='class_session',
        write_only=True,
        required=True
    )
    final_substitute = TeacherSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'requester', 'class_session', 'class_session_id',
            'date_of_leave', 'reason', 'status', 'status_display',
            'final_substitute', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'requester', 'status', 'final_substitute',
            'created_at', 'updated_at', 'status_display'
        ]
    
    def validate(self, data):
        """Validate leave request data."""
        request = self.context.get('request')
        class_session = data.get('class_session')
        date_of_leave = data.get('date_of_leave')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated.")
        
        # Check if date_of_leave is in the future
        if date_of_leave < timezone.now().date():
            raise serializers.ValidationError({
                'date_of_leave': 'Cannot request leave for past dates.'
            })
        
        # Check if the date matches the day of week of the class session
        target_day_of_week = date_of_leave.weekday()  # Monday=0, Sunday=6
        if class_session.day_of_week != target_day_of_week:
            raise serializers.ValidationError({
                'date_of_leave': f'Selected date ({date_of_weekday_name(date_of_leave)}) does not match class day ({class_session.get_day_of_week_display()}).'
            })
        
        # Check for existing active leave request for same teacher+date+class
        existing_request = LeaveRequest.objects.filter(
            requester__user=request.user,
            class_session=class_session,
            date_of_leave=date_of_leave,
            status__in=[LeaveRequest.Status.PENDING_HOD, LeaveRequest.Status.APPROVED_OPEN, LeaveRequest.Status.FILLED]
        ).exists()
        
        if existing_request:
            raise serializers.ValidationError(
                'An active leave request already exists for this class and date.'
            )
        
        return data


class SubstitutionProposalSerializer(serializers.ModelSerializer):
    """Serializer for SubstitutionProposal model."""
    request = LeaveRequestSerializer(read_only=True)
    request_id = serializers.PrimaryKeyRelatedField(
        queryset=LeaveRequest.objects.all(),
        source='request',
        write_only=True,
        required=True
    )
    proposed_teacher = TeacherSerializer(read_only=True)
    proposed_teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='proposed_teacher',
        write_only=True,
        required=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SubstitutionProposal
        fields = [
            'id', 'request', 'request_id',
            'proposed_teacher', 'proposed_teacher_id',
            'status', 'status_display',
            'message_from_requester',
            'sent_at', 'responded_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'sent_at', 'responded_at',
            'created_at', 'updated_at', 'status_display'
        ]


class CreateLeaveRequestSerializer(serializers.Serializer):
    """
    Serializer for creating a leave request with selected teachers.
    Used in POST /api/requests/create/
    """
    class_session_id = serializers.PrimaryKeyRelatedField(
        queryset=ClassSession.objects.all()
    )
    date = serializers.DateField()
    reason = serializers.CharField(max_length=500)
    selected_teacher_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=5  # Limit to 5 teachers per request
    )
    message = serializers.CharField(
        max_length=200, 
        required=False, 
        allow_blank=True
    )
    
    def validate(self, data):
        """Validate the leave request creation data."""
        request = self.context.get('request')
        class_session = data.get('class_session_id')
        date_of_leave = data.get('date')
        selected_teacher_ids = data.get('selected_teacher_ids')
        
        # Check if user is a teacher
        if not request.user.is_teacher:
            raise serializers.ValidationError(
                'Only teachers can create leave requests.'
            )
        
        # Get teacher profile
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError(
                'Teacher profile not found.'
            )
        
        # Check if teacher is assigned to this class
        if class_session.assigned_teacher != teacher:
            raise serializers.ValidationError(
                'You are not assigned to teach this class.'
            )
        
        # Validate date (same as LeaveRequestSerializer)
        if date_of_leave < timezone.now().date():
            raise serializers.ValidationError({
                'date': 'Cannot request leave for past dates.'
            })
        
        target_day_of_week = date_of_leave.weekday()
        if class_session.day_of_week != target_day_of_week:
            raise serializers.ValidationError({
                'date': f'Selected date ({date_of_weekday_name(date_of_leave)}) does not match class day ({class_session.get_day_of_week_display()}).'
            })
        
        # Validate selected teachers
        teachers = Teacher.objects.filter(id__in=selected_teacher_ids)
        if len(teachers) != len(selected_teacher_ids):
            raise serializers.ValidationError({
                'selected_teacher_ids': 'One or more teacher IDs are invalid.'
            })
        
        # Ensure teachers are from same department (for pilot phase)
        for teacher_obj in teachers:
            if teacher_obj.department != teacher.department:
                raise serializers.ValidationError({
                    'selected_teacher_ids': f'Teacher {teacher_obj.full_name} is not from your department.'
                })
        
        # Check if any teacher is the requester themselves
        if teacher in teachers:
            raise serializers.ValidationError({
                'selected_teacher_ids': 'Cannot select yourself as a substitute.'
            })
        
        # Store validated data for use in create method
        data['requester'] = teacher
        data['validated_teachers'] = teachers
        
        return data


class SubstituteRecommendationSerializer(serializers.Serializer):
    """
    Serializer for substitute teacher recommendations.
    Used in GET /api/substitutes/recommend/
    """
    teacher = TeacherSerializer()
    weekly_workload = serializers.IntegerField()
    is_available = serializers.BooleanField()
    is_qualified = serializers.BooleanField()
    is_on_leave = serializers.BooleanField()
    recommendation_score = serializers.FloatField()


class ProposalResponseSerializer(serializers.Serializer):
    """
    Serializer for responding to substitution proposals.
    Used in POST /api/proposals/{id}/respond/
    """
    action = serializers.ChoiceField(
        choices=['ACCEPT', 'REJECT'],
        required=True
    )
    message = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )


# Helper function
def date_of_weekday_name(date):
    """Convert date to weekday name."""
    return date.strftime('%A')