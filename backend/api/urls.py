from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login_view), # (Assuming you have this from before)
    path('profile/', views.get_profile),
    path('schedule/weekly/', views.get_weekly_schedule),
    path('substitutes/recommend/', views.recommend_substitutes),
    path('requests/create/', views.create_request),
    path('requests/<int:request_id>/respond/', views.respond_to_request),
    path('hod/requests/<int:request_id>/action/', views.hod_action),
    
    # --- NEW LINE HERE ---
    path('fcm/update/', views.update_fcm_token),
]