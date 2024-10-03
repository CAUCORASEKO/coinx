import logging
import pandas as pd
import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from web.forms import RegistrationForm, ApiKeyForm  # Asegúrate de que forms.py está bien ubicado
from web.models import UserProfile
from web.utils import APIs  # Importar la clase APIs desde utils.py
from cryptography.fernet import Fernet  # Importar para el cifrado
from web.management.commands.trade_signal import get_btc_data, get_symbol_data, select_random_symbols, analyze_trade
from web.management.commands.global_client import get_global_client  # Importar get_global_client



# Configuración del logger
logger = logging.getLogger(__name__)

# -----------------------------
# Vistas de páginas generales
# -----------------------------

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

            # Encriptar y almacenar las claves API
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

            messages.success(request, 'Por favor, revisa tu correo electrónico para confirmar tu cuenta.')
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
        'Confirma tu registro',
        f'Haz clic en el enlace para confirmar tu correo: {full_confirmation_url}',
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
        messages.success(request, 'Tu cuenta ha sido confirmada. Ya puedes iniciar sesión.')
        return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Token inválido o expirado.')
        return redirect('register')


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

    # Obtener balances de Spot y Futuros
    spot_balance = APIs.get_spot_balance(spot_client)
    futures_balance, detailed_futures_balances = APIs.get_futures_balance(futures_client)

    # Calcular el cambio en el portafolio
    portfolio_change = futures_balance - spot_balance
    portfolio_change_percentage = (portfolio_change / spot_balance) * 100 if spot_balance != 0 else 0

    # Simulación de datos de monedas (puedes reemplazarlo con datos reales)
    coins = [
        {'name': 'BTC', 'accounts': 'Spot', 'total': 1.2, 'available': 0.8, 'quantity': 1.2, 'price': 50000, 'price_24h': 49500},
        {'name': 'ETH', 'accounts': 'Futures', 'total': 2.5, 'available': 2.0, 'quantity': 2.5, 'price': 3000, 'price_24h': 3100},
    ]
    coins_count = len(coins)

    # Obtener señales desde `trade_signal.py`
    signal_data = None
    try:
        btc_data_1h = get_btc_data('1h', futures_client)  # Usamos `get_btc_data` de `trade_signal.py`
        btc_data_1d = get_btc_data('1d', futures_client)
        symbols = select_random_symbols(futures_client)

        for symbol in symbols:
            symbol_data = get_symbol_data(symbol, futures_client)
            if symbol_data:
                signal_data = analyze_trade(symbol, symbol_data, btc_data_1h, btc_data_1d, futures_client)
                if signal_data:  # Si encuentra una señal, se rompe el ciclo
                    break
    except Exception as e:
        logger.error(f"Error obteniendo señales: {e}")

    # Renderizar la plantilla del dashboard con las señales y datos
    return render(request, 'web/dashboard.html', {
        'spot_balance': spot_balance,
        'futures_balance': futures_balance,
        'detailed_futures_balances': detailed_futures_balances,
        'portfolio_change': portfolio_change,
        'portfolio_change_percentage': portfolio_change_percentage,
        'coins': coins,
        'coins_count': coins_count,
        'signal': signal_data,  # Enviar las señales al template
    })



# --------------------------
# Vista para obtener señales de trading
# --------------------------


# Ruta al archivo donde se almacenan las señales generadas por trade_signal.py
SIGNAL_FILE = os.path.join(os.path.dirname(__file__), 'signals.json')

@login_required
def get_signal(request):
    if request.method == 'POST':
        try:
            # Verificar si el archivo de señales existe
            if os.path.exists(SIGNAL_FILE):
                with open(SIGNAL_FILE, 'r') as file:
                    signal_data = json.load(file)

                if signal_data and signal_data.get('signal'):
                    return JsonResponse({'signal': signal_data})
                else:
                    return JsonResponse({'message': 'No signals available yet.'}, status=200)
            else:
                return JsonResponse({'message': 'No signal file found.'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Error decoding signal data.'}, status=500)

        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


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

            messages.success(request, 'Tus claves API han sido actualizadas.')
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
                'Tu nombre de usuario',
                f'Hola, tu nombre de usuario es {user.username}.',
                'noreply@yourdomain.com',  # Configura esto correctamente según tu servidor de correos
                [email],
                fail_silently=False,
            )
            messages.success(request, 'Se ha enviado un correo con tu nombre de usuario a tu dirección de email.')
            return redirect('index')  # Redirige al inicio
        except User.DoesNotExist:
            messages.error(request, 'No se encontró ningún usuario con esa dirección de email.')
            return render(request, 'web/username_recovery.html')

    return render(request, 'web/username_recovery.html')
