from django.db import models

# Create your models here.
"""
Database models for the Dynamic Teaching Workload Scheduler.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Add role-specific fields for authorization.
    """
    is_hod = models.BooleanField(default=False, verbose_name="Is HOD")
    is_teacher = models.BooleanField(default=False, verbose_name="Is Teacher")
    
    # Remove the default email field requirement
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({'HOD' if self.is_hod else 'Teacher' if self.is_teacher else 'Admin'})"


class Department(models.Model):
    """
    Represents an academic department.
    For pilot phase: Only "Electronics & Communication - ECE"
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    code = models.CharField(max_length=10, unique=True, verbose_name="Department Code")
    
    class Meta:
        db_table = 'departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        """Ensure code is uppercase."""
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class Teacher(models.Model):
    """
    Teacher profile extending the User model.
    Contains department-specific information.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='teacher_profile',
        verbose_name="User Account"
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='teachers',
        verbose_name="Department"
    )
    full_name = models.CharField(max_length=200, verbose_name="Full Name")
    fcm_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="FCM Token",
        help_text="Firebase Cloud Messaging token for push notifications"
    )
    employee_id = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Employee ID"
    )
    
    class Meta:
        db_table = 'teachers'
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"
    
    @property
    def is_hod(self):
        """Check if this teacher is also the HOD."""
        return self.user.is_hod
    
    @property
    def email(self):
        """Get email from associated user."""
        return self.user.email


class Subject(models.Model):
    """
    Academic subject offered by a department.
    """
    name = models.CharField(max_length=200, verbose_name="Subject Name")
    code = models.CharField(max_length=20, verbose_name="Subject Code")
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='subjects',
        verbose_name="Department"
    )
    
    class Meta:
        db_table = 'subjects'
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['code', 'name']
        unique_together = ['code', 'department']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class TeacherSubject(models.Model):
    """
    Junction table representing which teachers are qualified to teach which subjects.
    Many-to-many relationship between Teacher and Subject.
    """
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='qualified_subjects',
        verbose_name="Teacher"
    )
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='qualified_teachers',
        verbose_name="Subject"
    )
    
    class Meta:
        db_table = 'teacher_subjects'
        verbose_name = 'Teacher Subject Qualification'
        verbose_name_plural = 'Teacher Subject Qualifications'
        unique_together = ['teacher', 'subject']
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['subject']),
        ]
    
    def __str__(self):
        return f"{self.teacher.full_name} -> {self.subject.code}"


class ClassSession(models.Model):
    """
    Master timetable template representing recurring weekly class sessions.
    Handles variable daily schedules (not fixed 8-period grid).
    """
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    SEMESTER_CHOICES = [
        (3, '3rd Semester'),
        (5, '5th Semester'),
        (7, '7th Semester'),
    ]
    
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='class_sessions',
        verbose_name="Subject"
    )
    assigned_teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='assigned_sessions',
        verbose_name="Assigned Teacher"
    )
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK, 
        verbose_name="Day of Week"
    )
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    semester = models.IntegerField(
        choices=SEMESTER_CHOICES, 
        verbose_name="Semester"
    )
    section = models.CharField(
        max_length=1, 
        verbose_name="Section",
        help_text="Section letter (e.g., A, B, C)"
    )
    
    class Meta:
        db_table = 'class_sessions'
        verbose_name = 'Class Session'
        verbose_name_plural = 'Class Sessions'
        ordering = ['day_of_week', 'start_time', 'semester', 'section']
        # Unique constraint to prevent double booking a room/class
        unique_together = ['day_of_week', 'start_time', 'semester', 'section']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='end_time_after_start_time'
            ),
            models.CheckConstraint(
                check=models.Q(section__regex='^[A-Z]$'),
                name='section_single_uppercase_letter'
            ),
        ]
        indexes = [
            models.Index(fields=['day_of_week', 'start_time']),
            models.Index(fields=['semester', 'section']),
            models.Index(fields=['assigned_teacher']),
        ]
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}: {self.subject.code} (Sem {self.semester}{self.section})"
    
    @property
    def duration_minutes(self):
        """Calculate duration of class in minutes."""
        import datetime
        start = datetime.datetime.combine(datetime.date.today(), self.start_time)
        end = datetime.datetime.combine(datetime.date.today(), self.end_time)
        return int((end - start).total_seconds() / 60)


class LeaveRequest(models.Model):
    """
    Represents a request for leave where a teacher needs a substitute.
    """
    class Status(models.TextChoices):
        PENDING_HOD = 'PENDING_HOD', 'Pending HOD Approval'
        APPROVED_OPEN = 'APPROVED_OPEN', 'Approved - Open for Substitutes'
        FILLED = 'FILLED', 'Filled (Substitute Found)'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    requester = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='leave_requests',
        verbose_name="Requester"
    )
    class_session = models.ForeignKey(
        ClassSession, 
        on_delete=models.CASCADE, 
        related_name='leave_requests',
        verbose_name="Class Session"
    )
    date_of_leave = models.DateField(verbose_name="Date of Leave")
    reason = models.TextField(verbose_name="Reason for Leave")
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING_HOD,
        verbose_name="Status"
    )
    final_substitute = models.ForeignKey(
        Teacher, 
        on_delete=models.SET_NULL, 
        related_name='accepted_substitutions',
        null=True, 
        blank=True,
        verbose_name="Final Substitute"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    class Meta:
        db_table = 'leave_requests'
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ['-created_at']
        constraints = [
            # Prevent duplicate leave requests for same teacher+date+class
            models.UniqueConstraint(
                fields=['requester', 'class_session', 'date_of_leave'],
                condition=models.Q(status__in=['PENDING_HOD', 'APPROVED_OPEN', 'FILLED']),
                name='unique_active_leave_request'
            ),
        ]
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['date_of_leave']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Leave by {self.requester.full_name} on {self.date_of_leave} ({self.status})"
    
    def is_active(self):
        """Check if the leave request is still active."""
        return self.status in [self.Status.PENDING_HOD, self.Status.APPROVED_OPEN]


class SubstitutionProposal(models.Model):
    """
    Represents a proposal sent to a teacher to substitute for a leave request.
    Multiple proposals can be created per leave request.
    """
    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued (Not yet sent)'
        SENT = 'SENT', 'Sent to Teacher'
        ACCEPTED = 'ACCEPTED', 'Accepted by Teacher'
        REJECTED = 'REJECTED', 'Rejected by Teacher'
        AUTO_CANCELLED = 'AUTO_CANCELLED', 'Auto-Cancelled (Another teacher accepted)'
    
    request = models.ForeignKey(
        LeaveRequest, 
        on_delete=models.CASCADE, 
        related_name='substitution_proposals',
        verbose_name="Leave Request"
    )
    proposed_teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='substitution_proposals',
        verbose_name="Proposed Teacher"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.QUEUED,
        verbose_name="Status"
    )
    message_from_requester = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Message from Requester",
        help_text="Optional personal message to the substitute"
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Sent At")
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="Responded At")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    class Meta:
        db_table = 'substitution_proposals'
        verbose_name = 'Substitution Proposal'
        verbose_name_plural = 'Substitution Proposals'
        ordering = ['-created_at']
        constraints = [
            # Prevent duplicate proposals for same request+teacher
            models.UniqueConstraint(
                fields=['request', 'proposed_teacher'],
                condition=models.Q(status__in=['QUEUED', 'SENT']),
                name='unique_active_proposal'
            ),
        ]
        indexes = [
            models.Index(fields=['request', 'status']),
            models.Index(fields=['proposed_teacher', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Proposal: {self.proposed_teacher.full_name} for {self.request} ({self.status})"
    
    def is_active(self):
        """Check if the proposal is still active."""
        return self.status in [self.Status.QUEUED, self.Status.SENT]