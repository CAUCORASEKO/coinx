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



