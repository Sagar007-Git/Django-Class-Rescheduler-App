from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import views

urlpatterns = [
    # Auth
    path('auth/login/', obtain_auth_token), # Built-in Django Token Auth
    path('profile/', views.get_profile),

    # Schedule
    path('schedule/weekly/', views.get_weekly_schedule),

    # Substitution Workflow
    path('substitutes/recommend/', views.recommend_substitutes),
    path('requests/create/', views.create_request),
    path('requests/<int:request_id>/respond/', views.respond_to_request), # Accept/Reject

    # HOD
    path('hod/requests/<int:request_id>/action/', views.hod_action),
]