from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login_view),
    path('profile/', views.get_profile),
    path('schedule/weekly/', views.get_weekly_schedule),
    path('substitutes/recommend/', views.recommend_substitutes),
    path('requests/create/', views.create_request),
    
    # --- ADD THIS LINE (For Teachers) ---
    path('requests/user_requests/', views.get_user_requests), 

    path('requests/<int:request_id>/respond/', views.respond_to_request),
    
    # --- ADD THIS LINE (For HOD Dashboard) ---
    path('hod/requests/', views.get_hod_requests), 

    path('hod/requests/<int:request_id>/action/', views.hod_action),
]