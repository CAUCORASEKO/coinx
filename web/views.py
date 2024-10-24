# views.py 
import logging
import os
from web.models import Payment
from web.coinpayments_api import CoinPaymentsAPI
from django.shortcuts import render
from django.conf import settings
from binance.client import Client as FuturesClient  # Cliente de Futuros
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from web.forms import RegistrationForm, ApiKeyForm
from web.models import UserProfile
from cryptography.fernet import Fernet

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


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            # Validar que la clave de cifrado esté configurada correctamente
            if not settings.ENCRYPTION_KEY:
                if settings.DEBUG:
                    # Si estamos en modo de desarrollo (localhost), usar una clave de prueba
                    test_key = Fernet.generate_key()
                    fernet = Fernet(test_key)
                    print("Using a test encryption key for localhost. This should not be used in production.")
                else:
                    # En producción, lanzar un error si no está configurada la clave
                    messages.error(request, 'Encryption key is not set. Please contact support.')
                    return redirect('register')
            else:
                try:
                    # Convertir la clave a bytes y crear el objeto Fernet
                    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
                except Exception as e:
                    logger.error(f"Encryption error: {e}")
                    messages.error(request, 'Invalid encryption key configuration. Please contact support.')
                    return redirect('register')

            try:
                # Encriptar y almacenar las claves API
                api_key_encrypted = fernet.encrypt(form.cleaned_data['api_key'].encode())
                api_secret_encrypted = fernet.encrypt(form.cleaned_data['api_secret'].encode())
            except Exception as e:
                # Manejar cualquier error relacionado con el cifrado de datos
                logger.error(f"Encryption error: {e}")
                messages.error(request, 'An error occurred while encrypting your API keys. Please try again later.')
                return redirect('register')

            # Guardar perfil del usuario incluyendo otros datos del formulario
            UserProfile.objects.create(
                user=user,
                real_name=form.cleaned_data['real_name'],
                last_name=form.cleaned_data['last_name'],
                country=form.cleaned_data['country'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                phone_number=form.cleaned_data.get('phone_number', ''),  # Campo opcional
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

    # Cambia la URL según tu entorno
    if settings.DEBUG:
        full_confirmation_url = f'http://localhost:8000{confirmation_url}'
    else:
        full_confirmation_url = f'https://coinx-production.up.railway.app{confirmation_url}'

    # Enviar el email
    try:
        send_mail(
            'Confirm your registration',
            f'Click the link to confirm your email: {full_confirmation_url}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Error sending confirmation email: {e}")


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

from binance.client import Client as FuturesClient  # Esto ya está importado como FuturesClient

@login_required
def dashboard_view(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Desencriptar las claves API del usuario
    fernet = Fernet(settings.ENCRYPTION_KEY)
    api_key = fernet.decrypt(user_profile.api_key_encrypted).decode()
    api_secret = fernet.decrypt(user_profile.api_secret_encrypted).decode()

    # Crear cliente de Binance con las claves del usuario
    client = FuturesClient(api_key, api_secret)

    try:
        # Obtener balance en Spot
        account_info = client.get_account()  # Información de cuenta Spot
        spot_balance = sum(float(asset['free']) for asset in account_info['balances'] if float(asset['free']) > 0)

        # Obtener balance en Futuros
        futures_balance = sum(float(balance['balance']) for balance in client.futures_account_balance() if balance['asset'] == 'USDT')

        # Calcular el cambio en el portafolio
        portfolio_change = futures_balance - spot_balance
        portfolio_change_percentage = (portfolio_change / spot_balance) * 100 if spot_balance != 0 else 0

        # Obtener datos de las monedas en Spot (ejemplo de cómo obtener BTC y ETH)
        coins = []
        for asset in account_info['balances']:
            if float(asset['free']) > 0:  # Solo agregar si hay saldo disponible
                symbol = asset['asset']
                if symbol != 'USDT':  # Evitar USDT u otras monedas no deseadas
                    try:
                        # Obtener el precio de la moneda contra USDT
                        ticker = client.get_symbol_ticker(symbol=symbol + 'USDT')
                        price = float(ticker['price'])
                        coins.append({
                            'name': symbol,
                            'accounts': 'Spot',
                            'total': float(asset['free']),
                            'available': float(asset['free']),
                            'quantity': float(asset['free']),
                            'price': price,
                            'price_24h': price  # Esto puedes cambiarlo para obtener cambio en 24h.
                        })
                    except Exception as e:
                        # Si no existe un par de comercio para esta moneda, ignórala
                        logger.error(f"Error obteniendo datos para {symbol}: {e}")

        coins_count = len(coins)

    except Exception as e:
        logger.error(f"Error al obtener los datos de Binance: {e}")
        # Si falla la conexión con la API o cualquier error, mostrar valores simulados
        spot_balance = 0
        futures_balance = 0
        portfolio_change = 0
        portfolio_change_percentage = 0
        coins = []

    # Renderizar la plantilla del dashboard con las señales y datos
    return render(request, 'web/dashboard.html', {
        'spot_balance': spot_balance,
        'futures_balance': futures_balance,
        'portfolio_change': portfolio_change,
        'portfolio_change_percentage': portfolio_change_percentage,
        'coins': coins,
        'coins_count': coins_count,
    })

# Vista para actualizar claves API
@login_required
def update_api_keys(request):
    if request.method == 'POST':
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            # Actualizar las claves API
            user_profile = UserProfile.objects.get(user=request.user)
            fernet = Fernet(settings.ENCRYPTION_KEY)
            user_profile.api_key_encrypted = fernet.encrypt(form.cleaned_data['api_key'].encode())
            user_profile.api_secret_encrypted = fernet.encrypt(form.cleaned_data['api_secret'].encode())
            user_profile.save()

            messages.success(request, 'Your API keys have been updated.')
            return redirect('dashboard')
    else:
        form = ApiKeyForm()

    return render(request, 'web/update_api_keys.html', {'form': form})

# -----------------------------
# Recuperación de nombre de usuario
# -----------------------------

def username_recovery_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            send_mail(
                'Your Username',
                f'Hello, your username is {user.username}.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, 'An email with your username has been sent to your email address.')
            return redirect('index')
        except User.DoesNotExist:
            messages.error(request, 'No user found with that email address.')
            return render(request, 'web/username_recovery.html')

    return render(request, 'web/username_recovery.html')

# Vista para seleccionar el plan de pago


@login_required
def payment_subscription(request):
    if request.method == 'POST':
        plan = request.POST.get('plan')
        return redirect('payment_instructions', plan=plan)

    # Renderizar la plantilla de selección de plan de pago
    return render(request, 'web/payments/select_plan.html')


# Vista para mostrar las instrucciones de pago
@login_required
def payment_instructions(request, plan):
    # Definir el monto basado en el plan seleccionado
    if plan == 'monthly':
        amount = 20
        address = '0x376d4558b59DcF50f4275A4382806d05446dF654'
        network = 'Ethereum (ERC-20)'
        memo = None  # No se requiere memo para este plan
    elif plan == 'quarterly':
        amount = 50
        address = '0xD07A1a5A795E95468674D0ff886a70523FfD16c'
        network = 'BNB Smart Chain (BSC)'
        memo = None  # No se requiere memo para este plan
    elif plan == 'annual':
        amount = 100
        address = 'bnb1zdrqpt3zjs6k68rsest3xpun977uh2w9ywg5wf'
        memo = 'D85bfbfda9d654a40'  # Este plan requiere un memo específico
        network = 'BNB (Mainnet)'
    else:
        messages.error(request, 'Invalid plan selected.')
        return redirect('payment_subscription')

    # Renderizar la plantilla con las variables necesarias, incluyendo el memo
    return render(request, 'web/payments/instructions.html', {
        'plan': plan,
        'amount': amount,
        'address': address,
        'memo': memo,  # Asegúrate de pasar el memo a la plantilla
        'network': network
    })





@login_required
def create_payment(request, plan):
    # Inicializar la API con las llaves
    api = CoinPaymentsAPI(public_key=settings.COINPAYMENTS_API_KEY, private_key=settings.COINPAYMENTS_API_SECRET)

    # Definir el monto y otros parámetros basados en el plan seleccionado
    if plan == 'monthly':
        amount = 20
        memo = None
        network = 'Ethereum (ERC-20)'
    elif plan == 'quarterly':
        amount = 50
        memo = None
        network = 'BNB Smart Chain (BSC)'
    elif plan == 'annual':
        amount = 100
        memo = 'D85bfbfda9d654a40'  # Memo específico para el plan anual
        network = 'BNB Mainnet'
    else:
        messages.error(request, 'Invalid plan selected.')
        return redirect('payment_subscription')

    # Crear el pago usando la API de CoinPayments
    try:
        response = api.create_transaction(
            amount=amount,
            currency1='USDT',  # Moneda en la que se recibirá el pago
            currency2='USDT',  # Moneda del cliente
            buyer_email=request.user.email,
            item_name=f'Subscription plan: {plan}',
            custom=str(request.user.id)  # Asegúrate de convertir el ID a string
        )

        # Procesar la respuesta y mostrar la página de instrucciones de pago
        if response['error'] == 'ok':
            transaction_id = response['result']['txn_id']
            address = response['result']['address']
            amount_due = response['result']['amount']

            # Crear un registro del pago en la base de datos
            payment = Payment.objects.create(
                user=request.user,
                plan=plan,
                amount=amount_due,
                address=address,
                transaction_id=transaction_id,
                memo=memo,
                network=network,
                status='pending'  # Estado inicial
            )

            # Redirigir a la página de instrucciones de pago
            return render(request, 'web/payments/instructions.html', {
                'address': address,
                'amount': amount_due,
                'transaction_id': transaction_id,
                'memo': memo,  # Asegúrate de que el memo se envía aquí
                'plan': plan,
                'network': network
            })
        else:
            messages.error(request, f"Error creating transaction: {response['error']}")
            return redirect('payment_subscription')

    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('payment_subscription')
    


# User Payment status view 

@login_required
def payment_history(request):
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'web/payments/payment_history.html', {'payments': payments})
