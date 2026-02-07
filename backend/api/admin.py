from django.contrib import admin
from .models import Department, Subject, Teacher, ClassSession, LeaveRequest, SubstitutionProposal

# This registers your tables so they appear in the Admin Dashboard
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'department', 'is_hod')
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'

@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'subject', 'teacher')
    list_filter = ('day', 'teacher')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'date', 'time_slot', 'status')
    list_filter = ('status', 'date')

admin.site.register(SubstitutionProposal)