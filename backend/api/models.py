from django.db import models
from django.contrib.auth.models import User

# --- 1. STATIC DATA (Setup) ---

class Department(models.Model):
    name = models.CharField(max_length=100) # e.g., "ECE", "CSE"
    code = models.CharField(max_length=10, unique=True) # e.g., "04"

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100) # e.g., "VLSI Design"
    code = models.CharField(max_length=20, unique=True) # e.g., "EC501"
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE) # Links to auth_users
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject, related_name='qualified_teachers') # The "Teacher_Subjects" Table
    is_hod = models.BooleanField(default=False)
    fcm_token = models.CharField(max_length=255, blank=True, null=True) # For Notifications

    def __str__(self):
        return self.user.get_full_name()

# --- 2. RECURRING SCHEDULE (Template) ---

class ClassSession(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day = models.IntegerField(choices=DAYS_OF_WEEK) # 0=Monday, 1=Tuesday...
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=20)

    class Meta:
        unique_together = ('teacher', 'day', 'start_time') # Prevent double booking in template

    def __str__(self):
        return f"{self.subject} - {self.get_day_display()} {self.start_time}"

# --- 3. DYNAMIC TRANSACTIONS (The Workflow) ---

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING_HOD', 'Pending HOD Approval'),
        ('APPROVED_OPEN', 'Approved - Waiting for Sub'),
        ('FILLED', 'Filled by Substitute'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    requester = models.ForeignKey(Teacher, related_name='requests_made', on_delete=models.CASCADE)
    date = models.DateField()
    time_slot = models.TimeField() # Start time of the class to be covered
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_HOD')
    
    # The final substitute who accepted (Optimistic Locking Target)
    final_substitute = models.ForeignKey(Teacher, related_name='substitutions_filled', 
                                         null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.requester} - {self.date} ({self.status})"

class SubstitutionProposal(models.Model):
    """
    The individual invites sent to teachers.
    If Dr. Lee and Dr. Doe are both asked, we have 2 rows here.
    """
    request = models.ForeignKey(LeaveRequest, related_name='proposals', on_delete=models.CASCADE)
    candidate = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('request', 'candidate') # Don't ask the same person twice for one request

    def __str__(self):
        return f"Invite to {self.candidate} for Request #{self.request.id}"