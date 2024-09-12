"""
URL configuration for inversor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from web import views

urlpatterns = [
    # Home and registration
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),

    # Login and logout
    path('accounts/login/', auth_views.LoginView.as_view(template_name='web/registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),  # Logout and redirect to home

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Update API keys
    path('update-api-keys/', views.update_api_keys, name='update_api_keys'),  # Add this line for the API keys update view

    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='web/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='web/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='web/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='web/password_reset_complete.html'), name='password_reset_complete'),

    # Forgot Username
    path('username-recovery/', views.username_recovery_view, name='username_recovery'),
]
