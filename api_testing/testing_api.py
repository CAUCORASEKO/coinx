# Testing your API
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Claves API de Binance (coloca tus claves directamente aquí, pero recuerda que es inseguro dejar esto en producción)
api_key = 'YOUR_API_KEY'
api_secret = 'YOUR_API_SECRET'

# Start Binance client
client = Client(api_key, api_secret)

def get_futures_balance():
    try:
        # Get futures binance balance 
        futures_account = client.futures_account()
        
        # Print balance total USDT
        total_balance = float(futures_account['totalWalletBalance'])
        print(f"Total Balance Futures: {total_balance:.2f} USDT")
        
        # Print your coins balance
        print("\nBalance por activo:")
        for asset in futures_account['assets']:
            if float(asset['walletBalance']) > 0:
                print(f"{asset['asset']}: {float(asset['walletBalance']):.8f}")
    
    except BinanceAPIException as e:
        print(f"Error to get balance: {e}")

if __name__ == "__main__":
    get_futures_balance()
