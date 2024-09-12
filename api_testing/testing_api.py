# Testing your API
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Claves API de Binance (coloca tus claves directamente aquí, pero recuerda que es inseguro dejar esto en producción)
api_key = 'lSxB8SkFAKprXPA2zPkKg4PGVm6Ys9KKdK6Xbx9x5v3Nkq1t8s9bFrFXdh87yYxC'
api_secret = 'Ddyd7kwyLzOmHxuirdgaWDsR6oymL6iQ3zdGivHGHxhwrq5C90SUaf0Sqgg3yTow'

# Inicializar el cliente de Binance
client = Client(api_key, api_secret)

def get_futures_balance():
    try:
        # Obtener el balance de la cuenta de futuros
        futures_account = client.futures_account()
        
        # Imprimir el balance total en USDT
        total_balance = float(futures_account['totalWalletBalance'])
        print(f"Balance total de la cuenta de futuros: {total_balance:.2f} USDT")
        
        # Imprimir el balance de cada activo
        print("\nBalance por activo:")
        for asset in futures_account['assets']:
            if float(asset['walletBalance']) > 0:
                print(f"{asset['asset']}: {float(asset['walletBalance']):.8f}")
    
    except BinanceAPIException as e:
        print(f"Error al obtener el balance: {e}")

if __name__ == "__main__":
    get_futures_balance()
