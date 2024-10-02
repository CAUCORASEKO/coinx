from django.urls import path
from web import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Home and registration
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Login and logout
    path('accounts/login/', auth_views.LoginView.as_view(template_name='web/registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    # Update API keys
    path('update-api-keys/', views.update_api_keys, name='update_api_keys'),

    # Password reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='web/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='web/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='web/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='web/password_reset_complete.html'), 
         name='password_reset_complete'),

    # Username recovery URLs
    path('username-recovery/', views.username_recovery_view, name='username_recovery'),

    # Signal generation (nuevo)
    path('get_signal/', views.get_signal, name='get_signal'),  # Esta es la nueva ruta que faltaba
]
