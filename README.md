# Inversor Project - Automated Crypto Trading Platform

Welcome to the Inversor project! This platform is designed for automated cryptocurrency trading, offering a user-friendly interface for both novice and professional traders. The system integrates with multiple trading platforms and APIs, providing advanced automation tools and real-time tracking of investments.
Table of Contents

 - Features
 - Technologies Used
 - Installation
 - Configuration
 - Database Migrations
 - Running the Application
 - Testing
 - Directory Structure
 - Deployment
 - License

### Features

**The platform offers a comprehensive set of features for cryptocurrency trading**:

User Registration and Authentication: Secure account creation, login, logout, and email verification processes.

**API Key Managemen**t: Users can update their API keys for integrated trading platforms like Binance.

**Automated Trading Bots**: Includes support for various bots like Signal Bots, DCA Bots, TradingView Bots, and Grid Bots.

**Portfolio Tracking**: Real-time tracking of spot and futures accounts, including balance and transaction history.

**Payment Integration**: Payment subscription plans with integration to CoinPayments API for USDT payments.

**Password and Username Recovery**: Built-in system for password resets and username recovery.

**Admin Features**: Management of signals, user groups, notifications, and anti-leak measures for secure operations.

Technologies Used

 - Framework: Django (Python)
 - Front-end: HTML, CSS, JavaScript, Chart.js
 - Database: PostgreSQL (production), SQLite (development)
 - APIs: Binance API, CoinPayments API
 - Encryption: Cryptography using Fernet for secure API key storage
 - Deployment: Railway.app for cloud deployment

Installation

To set up the project locally, follow these steps:

**1.- Clone the Repository**:

    git clone https://github.com/your-username/inversor.git 
    cd inversor

**2.- Create a Virtual Environment**:

    python3 -m venv venv
    source venv/bin/activate  # On Windows use 'venv\Scripts\activate'

**3.- Install the Dependencies**:
    
    pip install -r requirements.txt


## Configuration
## Environment Variables

**Make sure to configure environment variables for secure setup. Create a .env file in the root of the project and add the following**:

    SECRET_KEY=your_secret_key
    DEBUG=True
    DATABASE_URL=your_postgresql_database_url  # For production
    EMAIL_HOST_USER=your_email
    EMAIL_HOST_PASSWORD=your_email_password
    COINPAYMENTS_API_KEY=your_coinpayments_public_key
    COINPAYMENTS_API_SECRET=your_coinpayments_private_key
    ENCRYPTION_KEY=your_fernet_encryption_key

## API Keys

Ensure you have valid API keys for Binance and CoinPayments and add them to the environment as shown above.

**Database Migrations**

To set up the database, run the following commands:

**Make Migrations**:
     
     python manage.py makemigrations

**Migrate**:

    python manage.py migrate

This will create the necessary tables and structures in the database.

## Running the Application
### Development Server

**To run the application locally**:

    python manage.py runserver

Access the application at http://127.0.0.1:8000/.

## Management Commands

**We have a custom management command to run the trading signals**:

    python manage.py run_signals


## Testing

**To run tests and ensure everything is functioning as expected**:

    python manage.py test

Make sure to set up a separate testing environment and database for best practices.

## Directory Structure

**Here's a quick overview of the main directories and files**:

**inversor/**: Root directory for Django settings and configurations.

**settings.py**: Application settings (database, API keys, etc.)
**urls.py**: Global URL routing configuration.
**wsgi.py**: WSGI configuration for deployment.


**web/**: Main app directory for the project.

**models.py**: Defines the database models (UserProfile, PaymentTransaction, etc.)
**views.py**: Contains the logic for handling HTTP requests and rendering templates.
**forms.py**: Forms for user registration and API key updates.
**templates/**: HTML templates for views like registration, login, dashboard, and more.
**static/**: Static files such as CSS, JavaScript, and images.

**management/commands/**: Custom management commands for background processes.


## Deployment

The application is configured to deploy on Railway.app. Make sure the environment variables are set in your Railway project for secure deployment.
Steps for Deployment

**Push the code to your GitHub repository.
Link your Railway project to the repository.
Configure the environment variables in Railway’s settings.
Deploy and access your application through the Railway domain.**

### License

This project is licensed under the MIT License. See the LICENSE file for more details.


# **Inversor-projekti - Automatisoitu kryptokaupankäyntialusta**

Tervetuloa Inversor-projektiin! Tämä alusta on suunniteltu automatisoitua kryptovaluuttakauppaa varten, ja se tarjoaa käyttäjäystävällisen käyttöliittymän sekä aloitteleville että kokeneille treidaajille. Järjestelmä integroituu useisiin kaupankäyntialustoihin ja API-rajapintoihin, tarjoten edistyneitä automaatiotyökaluja ja reaaliaikaisen sijoitusten seurannan.

## **Sisällysluettelo**

- [Ominaisuudet](#ominaisuudet)
- [Käytetyt teknologiat](#käytetyt-teknologiat)
- [Asennus](#asennus)
- [Konfigurointi](#konfigurointi)
- [Tietokannan migraatiot](#tietokannan-migraatiot)
- [Sovelluksen käynnistäminen](#sovelluksen-käynnistäminen)
- [Testaus](#testaus)
- [Hakemistorakenne](#hakemistorakenne)
- [Käyttöönotto](#käyttöönotto)
- [Lisenssi](#lisenssi)

---

## **Ominaisuudet**

Alusta tarjoaa kattavan valikoiman ominaisuuksia kryptokaupankäyntiin:

- **Käyttäjien rekisteröinti ja todennus**: Turvallinen tilin luominen, kirjautuminen, uloskirjautuminen ja sähköpostivarmennus.
- **API-avainten hallinta**: Käyttäjät voivat päivittää API-avaimensa kaupankäyntialustoille, kuten Binanceen.
- **Automaattiset kaupankäyntibotit**: Tuki eri bottityypeille, kuten signaalibotit, DCA-botit, TradingView-botit ja Grid-botit.
- **Salkun seuranta**: Reaaliaikainen seuranta spot- ja futuuritileille, mukaan lukien saldo- ja tapahtumahistoria.
- **Maksujen integrointi**: Maksusuunnitelmat CoinPayments API -integraatiolla USDT-maksuja varten.
- **Salasanan ja käyttäjätunnuksen palautus**: Järjestelmä salasanan ja käyttäjätunnuksen palautusta varten.
- **Ylläpito-ominaisuudet**: Signaalien hallinta, käyttäjäryhmät, ilmoitukset ja anti-leak-toiminnot turvallista käyttöä varten.

## **Käytetyt teknologiat**

- **Framework**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **Tietokanta**: PostgreSQL (tuotanto), SQLite (kehitys)
- **API:t**: Binance API, CoinPayments API
- **Salaus**: Kryptografiaa käyttäen Fernet-salausta API-avainten turvalliseen tallennukseen
- **Käyttöönotto**: Railway.app pilvikäyttöön

## **Asennus**

Projektin asennus paikallisesti:

1. **Kloonaa repository**:
   ```bash
   git clone https://github.com/your-username/inversor.git
   cd inversor

2. **Luo virtuaaliympäristö**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windowsissa käytä 'venv\Scripts\activate'

3. **Asenna riippuvuudet**:
   ```bash
   pip install -r requirements.txt


## Konfigurointi

### Ympäristömuuttujat

Varmista, että ympäristömuuttujat on asetettu turvallista asennusta varten. Luo `.env`-tiedosto projektin juureen ja lisää seuraavat muuttujat:

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=your_postgresql_database_url  # tuotantoa varten
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_email_password
COINPAYMENTS_API_KEY=your_coinpayments_public_key
COINPAYMENTS_API_SECRET=your_coinpayments_private_key
ENCRYPTION_KEY=your_encryption_key
```

**Muistutus**: Muista vaihtaa DEBUG tilaan False tuotantoympäristössä.