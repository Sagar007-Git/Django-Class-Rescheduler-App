"""
Admin configuration for the API app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Department, Teacher, Subject,
    TeacherSubject, ClassSession, LeaveRequest,
    SubstitutionProposal
)


class UserAdmin(BaseUserAdmin):
    """Custom User admin with additional fields."""
    list_display = ('username', 'email', 'first_name', 'last_name', 
                   'is_hod', 'is_teacher', 'is_staff', 'is_active')
    list_filter = ('is_hod', 'is_teacher', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role Information', {
            'fields': ('is_hod', 'is_teacher'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role Information', {
            'fields': ('is_hod', 'is_teacher'),
        }),
    )


class DepartmentAdmin(admin.ModelAdmin):
    """Department admin configuration."""
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',)


class TeacherAdmin(admin.ModelAdmin):
    """Teacher admin configuration."""
    list_display = ('full_name', 'employee_id', 'department', 'is_hod')
    list_filter = ('department',)
    search_fields = ('full_name', 'employee_id', 'user__username')
    raw_id_fields = ('user', 'department')
    
    def is_hod(self, obj):
        return obj.user.is_hod
    is_hod.boolean = True
    is_hod.short_description = 'Is HOD'


class SubjectAdmin(admin.ModelAdmin):
    """Subject admin configuration."""
    list_display = ('name', 'code', 'department')
    list_filter = ('department',)
    search_fields = ('name', 'code')
    ordering = ('code',)


class TeacherSubjectAdmin(admin.ModelAdmin):
    """TeacherSubject admin configuration."""
    list_display = ('teacher', 'subject')
    list_filter = ('subject__department',)
    search_fields = ('teacher__full_name', 'subject__name')
    raw_id_fields = ('teacher', 'subject')


class ClassSessionAdmin(admin.ModelAdmin):
    """ClassSession admin configuration."""
    list_display = ('get_day_display', 'start_time', 'end_time', 
                   'subject', 'assigned_teacher', 'semester', 'section')
    list_filter = ('day_of_week', 'semester', 'section', 'subject__department')
    search_fields = ('subject__name', 'assigned_teacher__full_name')
    raw_id_fields = ('subject', 'assigned_teacher')
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Day'


class LeaveRequestAdmin(admin.ModelAdmin):
    """LeaveRequest admin configuration."""
    list_display = ('requester', 'date_of_leave', 'class_session', 
                   'status', 'final_substitute', 'created_at')
    list_filter = ('status', 'date_of_leave', 'requester__department')
    search_fields = ('requester__full_name', 'reason')
    raw_id_fields = ('requester', 'class_session', 'final_substitute')
    date_hierarchy = 'date_of_leave'


class SubstitutionProposalAdmin(admin.ModelAdmin):
    """SubstitutionProposal admin configuration."""
    list_display = ('proposed_teacher', 'request', 'status', 
                   'sent_at', 'responded_at')
    list_filter = ('status', 'request__date_of_leave')
    search_fields = ('proposed_teacher__full_name', 
                    'request__requester__full_name')
    raw_id_fields = ('request', 'proposed_teacher')
    date_hierarchy = 'created_at'


# Register models with admin site
admin.site.register(User, UserAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Teacher, TeacherAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(TeacherSubject, TeacherSubjectAdmin)
admin.site.register(ClassSession, ClassSessionAdmin)
admin.site.register(LeaveRequest, LeaveRequestAdmin)
admin.site.register(SubstitutionProposal, SubstitutionProposalAdmin)