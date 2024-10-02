from binance.client import Client  # Cliente para Spot y Futures
from binance.exceptions import BinanceAPIException
import logging

# Configurar el logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIs:
    @classmethod
    def get_spot_client_instance(cls, api_key, api_secret):
        """Devuelve una instancia del cliente Spot"""
        try:
            return Client(api_key, api_secret)  # Cliente de Spot
        except BinanceAPIException as e:
            logger.error(f"Error al conectar con Binance Spot: {e}")
            raise ValueError(f"Error al conectar con Binance Spot: {e}")

    @classmethod
    def get_futures_client_instance(cls, api_key, api_secret):
        """Devuelve una instancia del cliente Futures"""
        try:
            return Client(api_key, api_secret)  # Cliente de Futures también es manejado por Client
        except BinanceAPIException as e:
            logger.error(f"Error al conectar con Binance Futures: {e}")
            raise ValueError(f"Error al conectar con Binance Futures: {e}")

    @classmethod
    def get_spot_balance(cls, spot_client):
        """Obtiene el balance total de Spot"""
        account_info = spot_client.get_account()
        total_spot_balance = 0.0

        # Sumar los balances de las monedas que tienen un balance libre
        for balance in account_info['balances']:
            free_balance = float(balance['free'])
            if free_balance > 0:
                total_spot_balance += free_balance

        return total_spot_balance

    @classmethod
    def get_futures_balance(cls, futures_client):
        """Obtiene el balance total y disponible de Futures"""
        account_info = futures_client.futures_account()
        total_futures_balance = 0.0
        futures_balances = []

        # Iterar sobre los activos y obtener el balance disponible
        for asset in account_info['assets']:
            wallet_balance = float(asset['walletBalance'])
            available_balance = float(asset['availableBalance'])  # Balance disponible para trading
            if wallet_balance > 0 or available_balance > 0:  # Solo mostrar si hay balance
                futures_balances.append({
                    'asset': asset['asset'],
                    'wallet_balance': wallet_balance,
                    'available_balance': available_balance,
                    'unrealized_pnl': float(asset['unrealizedProfit']),
                    'margin_balance': float(asset['marginBalance'])
                })
                total_futures_balance += available_balance  # Sumamos solo el balance disponible

        return total_futures_balance, futures_balances