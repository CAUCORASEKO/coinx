# views.py
import logging
import os
from web.models import Payment
from web.coinpayments_api import CoinPaymentsAPI
from django.shortcuts import render
from django.conf import settings
from binance.client import Client as FuturesClient  # Futuuri-asiakas
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

# Loggerin konfigurointi
logger = logging.getLogger(__name__)

# -----------------------------
# Yleiset näkymät
# -----------------------------

# Etusivu
def index(request):
    return render(request, 'web/index.html')


# -------------------------------------------
# Käyttäjän rekisteröinti- ja kirjautumisnäkymät
# -------------------------------------------

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            # Varmista, että salausavain on asetettu oikein
            if not settings.ENCRYPTION_KEY:
                if settings.DEBUG:
                    # Kehitystilassa (localhost), käytetään testisalausavainta
                    test_key = Fernet.generate_key()
                    fernet = Fernet(test_key)
                    print("Testisalausavainta käytetään localhostissa. Tämä ei saa olla käytössä tuotannossa.")
                else:
                    # Tuotannossa, jos avain puuttuu, näytetään virhe
                    messages.error(request, 'Encryption key is not set. Please contact support.')
                    return redirect('register')
            else:
                try:
                    # Muutetaan avain tavuiksi ja luodaan Fernet-objekti
                    fernet = Fernet(settings.ENCRYPTION_KEY)
                except Exception as e:
                    logger.error(f"Encryption error: {e}")
                    messages.error(request, 'Invalid encryption key configuration. Please contact support.')
                    return redirect('register')

            try:
                # Salaa ja tallenna API-avaimet bytes muodossa
                api_key_encrypted = fernet.encrypt(form.cleaned_data['api_key'].encode('utf-8'))
                api_secret_encrypted = fernet.encrypt(form.cleaned_data['api_secret'].encode('utf-8'))
            except Exception as e:
                # Käsittele mahdolliset salausvirheet
                logger.error(f"Encryption error: {e}")
                messages.error(request, 'An error occurred while encrypting your API keys. Please try again later.')
                return redirect('register')

            # Tallenna käyttäjän profiili ja muut tiedot
            UserProfile.objects.create(
                user=user,
                real_name=form.cleaned_data['real_name'],
                last_name=form.cleaned_data['last_name'],
                country=form.cleaned_data['country'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                phone_number=form.cleaned_data.get('phone_number', ''),  # Valinnainen kenttä
                platform=form.cleaned_data['platform'],
                api_key_encrypted=api_key_encrypted,  # API-avaimet tallennetaan kryptattuna
                api_secret_encrypted=api_secret_encrypted,
            )

            # Lähetä vahvistusviesti sähköpostitse
            send_confirmation_email(user)

            messages.success(request, 'Please check your email to confirm your account.')
            return redirect('login')
    else:
        form = RegistrationForm()

    return render(request, 'web/register.html', {'form': form})



# Funktio vahvistusviestin lähettämiseksi
def send_confirmation_email(user):
    user_profile = UserProfile.objects.get(user=user)
    token = user_profile.email_confirmation_token
    confirmation_url = reverse('confirm_email', args=[token])

    # Muuta URL ympäristön mukaan
    if settings.DEBUG:
        full_confirmation_url = f'http://localhost:8000{confirmation_url}'
    else:
        full_confirmation_url = f'https://coinx-production.up.railway.app{confirmation_url}'

    # Lähetä sähköposti
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


# Sähköpostin vahvistusnäkymä
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
# Dashboard-näkymät
# --------------------------


@login_required
def dashboard_view(request):
    # Hae käyttäjän profiili
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Tarkista, ovatko API-avaimet tyhjiä tai puuttuvat
    if not user_profile.api_key_encrypted or not user_profile.api_secret_encrypted:
        # Jos avaimet puuttuvat, ohjaa API-avainten päivityssivulle
        messages.info(request, 'Päivitä API-avaimesi päästäksesi hallintapaneeliin.')
        return redirect('update_api_keys')  # Varmista, että 'update_api_keys' on määritelty URL-tiedostossasi

    # Jos avaimet ovat olemassa, jatka niiden purkamista ja lataa *hallintapaneeli*
    fernet = Fernet(settings.ENCRYPTION_KEY)
    api_key = fernet.decrypt(user_profile.api_key_encrypted).decode()
    api_secret = fernet.decrypt(user_profile.api_secret_encrypted).decode()

    client = FuturesClient(api_key, api_secret)

    # Täällä haetaan käyttäjän tiedot Binancesta ja renderöidään hallintapaneeli
    try:
        account_info = client.get_account()
        spot_balance = sum(float(asset['free']) for asset in account_info['balances'] if float(asset['free']) > 0)
        futures_balance = sum(float(balance['balance']) for balance in client.futures_account_balance() if balance['asset'] == 'USDT')
        portfolio_change = futures_balance - spot_balance
        portfolio_change_percentage = (portfolio_change / spot_balance) * 100 if spot_balance != 0 else 0

        coins = []
        for asset in account_info['balances']:
            if float(asset['free']) > 0:
                symbol = asset['asset']
                if symbol != 'USDT':
                    try:
                        ticker = client.get_symbol_ticker(symbol=symbol + 'USDT')
                        price = float(ticker['price'])
                        coins.append({
                            'name': symbol,
                            'accounts': 'Spot',
                            'total': float(asset['free']),
                            'available': float(asset['free']),
                            'quantity': float(asset['free']),
                            'price': price,
                            'price_24h': price
                        })
                    except Exception as e:
                        logger.error(f"Virhe kolikkotietojen hakemisessa {symbol}: {e}")

        coins_count = len(coins)

    except Exception as e:
        logger.error(f"Virhe tietojen hakemisessa Binancesta: {e}")
        spot_balance = 0
        futures_balance = 0
        portfolio_change = 0
        portfolio_change_percentage = 0
        coins = []

    return render(request, 'web/dashboard.html', {
        'spot_balance': spot_balance,
        'futures_balance': futures_balance,
        'portfolio_change': portfolio_change,
        'portfolio_change_percentage': portfolio_change_percentage,
        'coins': coins,
        'coins_count': coins_count,
    })



# Näkymä API-avainten päivittämiseen
@login_required  # Varmistaa, että käyttäjä on kirjautunut sisään ennen tämän toiminnon käyttämistä
def update_api_keys(request):
    # Tarkistetaan, onko tämä POST-pyyntö, eli lähetettiinkö lomake
    if request.method == 'POST':
        form = ApiKeyForm(request.POST)  # Luodaan lomakeobjekti käyttäjän syöttämistä tiedoista
        # Tarkistetaan, onko lomake oikein täytetty ja validoitu
        if form.is_valid():
            # Hae kirjautuneen käyttäjän profiili
            user_profile = UserProfile.objects.get(user=request.user)
            fernet = Fernet(settings.ENCRYPTION_KEY)  # Käytetään salausavainta tietojen salaamiseen

            # Salaa ja tallenna API-avain käyttäjäprofiiliin
            user_profile.api_key_encrypted = fernet.encrypt(form.cleaned_data['api_key'].encode('utf-8'))
            # Salaa ja tallenna API-salaisuus käyttäjäprofiiliin
            user_profile.api_secret_encrypted = fernet.encrypt(form.cleaned_data['api_secret'].encode('utf-8'))
            user_profile.save()  # Tallennetaan päivitykset tietokantaan

            # Näytetään käyttäjälle onnistumisviesti
            messages.success(request, 'API-avaimesi on päivitetty.')
            return redirect('dashboard')  # Ohjaa käyttäjä takaisin hallintapaneeliin päivityksen jälkeen
    else:
        form = ApiKeyForm()  # Jos pyyntö ei ole POST, luodaan tyhjä lomake käyttäjän täytettäväksi

    # Renderöi (näyttää) update_api_keys.html-mallin, jossa on lomake
    return render(request, 'web/update_api_keys.html', {'form': form})



# -----------------------------
# Käyttäjänimen palautus
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

# Näkymä maksusuunnitelman valintaan
@login_required
def payment_subscription(request):
    if request.method == 'POST':
        plan = request.POST.get('plan')
        return redirect('payment_instructions', plan=plan)

    # Renderöidään maksusuunnitelman valintasivu
    return render(request, 'web/payments/select_plan.html')


# Näkymä maksun ohjeiden näyttämiseen
@login_required
def payment_instructions(request, plan):
    # Määritellään summa valitun suunnitelman mukaan
    if plan == 'monthly':
        amount = 20
        address = '0x376d4558b59DcF50f4275A4382806d05446dF654'
        network = 'Ethereum (ERC-20)'
        memo = None  # Tätä suunnitelmaa ei vaadita muistioon
    elif plan == 'quarterly':
        amount = 50
        address = '0xD07A1a5A795E95468674D0ff886a70523FfD16c'
        network = 'BNB Smart Chain (BSC)'
        memo = None  # Tätä suunnitelmaa ei vaadita muistioon
    elif plan == 'annual':
        amount = 100
        address = 'bnb1zdrqpt3zjs6k68rsest3xpun977uh2w9ywg5wf'
        memo = 'D85bfbfda9d654a40'  # Tämä suunnitelma vaatii tietyn muiston
        network = 'BNB (Mainnet)'
    else:
        messages.error(request, 'Invalid plan selected.')
        return redirect('payment_subscription')

    # Renderöidään maksusivun malli tarvittavilla muuttujilla, mukaan lukien memo
    return render(request, 'web/payments/instructions.html', {
        'plan': plan,
        'amount': amount,
        'address': address,
        'memo': memo,  # Varmista, että memo välitetään malliin
        'network': network
    })

@login_required
def create_payment(request, plan):
    # Alustetaan API avaimilla
    api = CoinPaymentsAPI(public_key=settings.COINPAYMENTS_API_KEY, private_key=settings.COINPAYMENTS_API_SECRET)

    # Määritellään summa ja muut parametrit valitun suunnitelman mukaan
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
        memo = 'D85bfbfda9d654a40'  # Erityinen memo vuosittaiselle suunnitelmalle
        network = 'BNB Mainnet'
    else:
        messages.error(request, 'Invalid plan selected.')
        return redirect('payment_subscription')

    # Luo maksu CoinPayments API:n avulla
    try:
        response = api.create_transaction(
            amount=amount,
            currency1='USDT',  # Maksun valuutta
            currency2='USDT',  # Asiakkaan valuutta
            buyer_email=request.user.email,
            item_name=f'Subscription plan: {plan}',
            custom=str(request.user.id)  # Muunna ID stringiksi
        )

        # Käsitellään vastaus ja näytetään maksun ohjesivu
        if response['error'] == 'ok':
            transaction_id = response['result']['txn_id']
            address = response['result']['address']
            amount_due = response['result']['amount']

            # Luo maksutapahtuma tietokantaan
            payment = Payment.objects.create(
                user=request.user,
                plan=plan,
                amount=amount_due,
                address=address,
                transaction_id=transaction_id,
                memo=memo,
                network=network,
                status='pending'  # Alustava tila
            )

            # Ohjaa maksun ohjesivulle
            return render(request, 'web/payments/instructions.html', {
                'address': address,
                'amount': amount_due,
                'transaction_id': transaction_id,
                'memo': memo,  # Varmista, että memo välitetään täällä
                'plan': plan,
                'network': network
            })
        else:
            messages.error(request, f"Error creating transaction: {response['error']}")
            return redirect('payment_subscription')

    except Exception as e:
        logger.error(f"Virhe luotaessa tapahtumaa: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('payment_subscription')

# Käyttäjän maksuhistorian näkymä
@login_required
def payment_history(request):
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'web/payments/payment_history.html', {'payments': payments})
