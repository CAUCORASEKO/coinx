# utils.py
from binance.client import Client  # Asiakas Spot- ja Futures-kauppaa varten
from binance.exceptions import BinanceAPIException
import logging

# Asetetaan lokitus
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIs:
    @classmethod
    def get_spot_client_instance(cls, api_key, api_secret):
        """Palauttaa Spot-asiakkaan instanssin"""
        try:
            return Client(api_key, api_secret)  # Spot-asiakas
        except BinanceAPIException as e:
            logger.error(f"Virhe yhteydessä Binance Spotiin: {e}")
            raise ValueError(f"Virhe yhteydessä Binance Spotiin: {e}")

    @classmethod
    def get_futures_client_instance(cls, api_key, api_secret):
        """Palauttaa Futures-asiakkaan instanssin"""
        try:
            return Client(api_key, api_secret)  # Futures-asiakas myös hoidettu Client-luokassa
        except BinanceAPIException as e:
            logger.error(f"Virhe yhteydessä Binance Futuresiin: {e}")
            raise ValueError(f"Virhe yhteydessä Binance Futuresiin: {e}")

    @classmethod
    def get_spot_balance(cls, spot_client):
        """Hakee Spot-tilin kokonaisaldon"""
        account_info = spot_client.get_account()
        total_spot_balance = 0.0

        # Lasketaan yhteen valuuttojen saldot, joilla on vapaata saldoa
        for balance in account_info['balances']:
            free_balance = float(balance['free'])
            if free_balance > 0:
                total_spot_balance += free_balance

        return total_spot_balance

    @classmethod
    def get_futures_balance(cls, futures_client):
        """Hakee Futures-tilin kokonais- ja käytettävissä olevan saldon"""
        account_info = futures_client.futures_account()
        total_futures_balance = 0.0
        futures_balances = []

        # Käydään läpi omaisuuserät ja haetaan käytettävissä oleva saldo
        for asset in account_info['assets']:
            wallet_balance = float(asset['walletBalance'])
            available_balance = float(asset['availableBalance'])  # Käytettävissä oleva saldo kaupankäyntiin
            if wallet_balance > 0 or available_balance > 0:  # Näytetään vain, jos on saldoa
                futures_balances.append({
                    'asset': asset['asset'],
                    'wallet_balance': wallet_balance,
                    'available_balance': available_balance,
                    'unrealized_pnl': float(asset['unrealizedProfit']),
                    'margin_balance': float(asset['marginBalance'])
                })
                total_futures_balance += available_balance  # Lasketaan vain käytettävissä oleva saldo

        return total_futures_balance, futures_balances

    @classmethod
    def get_futures_account_info(cls, futures_client):
        """Hakee Futures-tilin tiedot"""
        try:
            # Binance API -kutsu
            response = futures_client.futures_account()
            # Tarkistetaan, onko vastaus kelvollinen sanakirja
            if not isinstance(response, dict):
                logger.error(f"API:sta saatu odottamaton vastaus: {response}")
                return None
            
            return response
        except BinanceAPIException as e:
            logger.error(f"Virhe Futures-tilin tietojen hakemisessa: {e}")
            return None
