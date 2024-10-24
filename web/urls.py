# web/urls.py 
from django.urls import path
from django.contrib.auth import views as auth_views
from web import views

urlpatterns = [
    # Koti- ja rekisteröintisivut
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),

    # Kirjautumis- ja uloskirjautumissivut
    path('accounts/login/', auth_views.LoginView.as_view(template_name='web/registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),

    # Käyttäjän hallintapaneeli
    path('dashboard/', views.dashboard_view, name='dashboard'),
    #path('get_signal/', views.get_signal, name='get_signal'),  # Poistettu käytöstä, jos ei tarvita

    # API-avainten päivityssivu
    path('update-api-keys/', views.update_api_keys, name='update_api_keys'),

    # Salasanan nollaus-URL:t
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

    # Käyttäjätunnuksen palautus-URL
    path('username-recovery/', views.username_recovery_view, name='username_recovery'),

    # Maksusivujen URL:t
    path('payment/', views.payment_subscription, name='payment_subscription'),
    path('payment/instructions/<str:plan>/', views.payment_instructions, name='payment_instructions'),  # Maksuohjeiden URL
]
