from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from .forms import RegistrationForm, ApiKeyForm
from .models import UserProfile
from .utils import APIs  # Importar la clase APIs desde utils.py
from cryptography.fernet import Fernet  # Importar para el cifrado
from binance.client import Client  # Importar el cliente de Binance
import logging

# Configuración de logger
logger = logging.getLogger(__name__)

# -----------------------------
# Vistas de páginas generales
# ----------------------------

# Página de inicio
def index(request):
    return render(request, 'web/index.html')


# -------------------------------------------
# Vistas de autenticación y registro de usuarios
# -------------------------------------------

# Vista de registro de usuarios
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            # Encrypt and store API keys
            fernet = Fernet(settings.ENCRYPTION_KEY)
            api_key_encrypted = fernet.encrypt(form.cleaned_data['api_key'].encode())
            api_secret_encrypted = fernet.encrypt(form.cleaned_data['api_secret'].encode())

            # Guardar perfil del usuario incluyendo otros datos del formulario
            UserProfile.objects.create(
                user=user,
                real_name=form.cleaned_data['real_name'],
                last_name=form.cleaned_data['last_name'],
                country=form.cleaned_data['country'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                phone_number=form.cleaned_data['phone_number'],  # Campo opcional
                platform=form.cleaned_data['platform'],
                api_key_encrypted=api_key_encrypted,
                api_secret_encrypted=api_secret_encrypted,
            )

            # Enviar email de confirmación
            send_confirmation_email(user)

            messages.success(request, 'Please check your email to confirm your account.')
            return redirect('login')
    else:
        form = RegistrationForm()

    return render(request, 'web/register.html', {'form': form})


# Función para enviar email de confirmación
def send_confirmation_email(user):
    user_profile = UserProfile.objects.get(user=user)
    token = user_profile.email_confirmation_token
    confirmation_url = reverse('confirm_email', args=[token])
    full_confirmation_url = f'http://localhost:8000{confirmation_url}'  # Cambiar a la URL de producción

    # Enviar el email
    send_mail(
        'Confirm your registration',
        f'Click the link to confirm your email: {full_confirmation_url}',
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )


# Vista para confirmar el email
def confirm_email(request, token):
    try:
        user_profile = UserProfile.objects.get(email_confirmation_token=token)
        user = user_profile.user
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been confirmed. You can now log in.')
        return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Invalid or expired token.')
        return redirect('register')


# --------------------------
# Vistas del dashboard
# --------------------------

# --------------------------
# Vistas del dashboard
# --------------------------

@login_required
def dashboard_view(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    api_key = user_profile.get_api_key()
    api_secret = user_profile.get_api_secret()

    # Obtener cliente Spot y Futuros
    spot_client = APIs.get_spot_client_instance(api_key, api_secret)
    futures_client = APIs.get_futures_client_instance(api_key, api_secret)

    # Obtener balances de Spot
    spot_balance = APIs.get_spot_balance(spot_client)

    # Obtener balances de Futuros
    futures_balance, detailed_futures_balances = APIs.get_futures_balance(futures_client)

    return render(request, 'web/dashboard.html', {
        'spot_balance': spot_balance,
        'futures_balance': futures_balance,
        'detailed_futures_balances': detailed_futures_balances
    })


# Vista para actualizar claves API
@login_required
def update_api_keys(request):
    if request.method == 'POST':
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            # Usar la clase APIs para almacenar las claves API
            api_key = form.cleaned_data['api_key']
            api_secret = form.cleaned_data['api_secret']

            # Almacenar las claves API en la clase APIs
            APIs.set_api_key(request.user.id, api_key)
            APIs.set_api_secret(request.user.id, api_secret)

            messages.success(request, 'Your API keys have been updated.')
            return redirect('dashboard')
    else:
        form = ApiKeyForm()

    return render(request, 'web/update_api_keys.html', {'form': form})


# -----------------------------
# Recuperación de nombre de usuario
# -----------------------------

# Vista para recuperación de nombre de usuario
def username_recovery_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Enviar correo con el nombre de usuario
            send_mail(
                'Your Username',
                f'Hello, your username is {user.username}.',
                'noreply@yourdomain.com',  # Configura esto correctamente según tu servidor de correos
                [email],
                fail_silently=False,
            )
            messages.success(request, 'An email with your username has been sent to your email address.')
            return redirect('index')  # Redirige al inicio en lugar de mostrar otra página
        except User.DoesNotExist:
            messages.error(request, 'No user found with that email address.')
            return render(request, 'web/username_recovery.html')

    return render(request, 'web/username_recovery.html')