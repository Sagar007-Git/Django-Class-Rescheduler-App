"""
URL configuration for the API app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    CustomTokenObtainPairView,
    DepartmentViewSet,
    TeacherViewSet,
    SubjectViewSet,
    TeacherSubjectViewSet,
    ClassSessionViewSet,
    LeaveRequestViewSet,
    SubstitutionProposalViewSet,
    WeeklyScheduleView,
    SubstituteRecommendationView,
    CreateLeaveRequestView,
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'teacher-subjects', TeacherSubjectViewSet)
router.register(r'class-sessions', ClassSessionViewSet)
router.register(r'leave-requests', LeaveRequestViewSet)
router.register(r'substitution-proposals', SubstitutionProposalViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    # JWT Authentication
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Core API endpoints
    path('schedule/my-weekly/', WeeklyScheduleView.as_view(), name='weekly_schedule'),
    path('substitutes/recommend/', SubstituteRecommendationView.as_view(), name='recommend_substitutes'),
    path('requests/create/', CreateLeaveRequestView.as_view(), name='create_leave_request'),
    
    # Include router URLs
    path('', include(router.urls)),
    
    # User endpoints
    path('user/me/', TeacherViewSet.as_view({'get': 'me'}), name='user_me'),
]