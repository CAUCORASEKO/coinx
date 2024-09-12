from binance.client import Client

def get_binance_data(api_key, api_secret):
    client = Client(api_key, api_secret)
    
    try:
        # Obtener balances de la cuenta Spot
        account_info = client.get_account()
        balances = account_info['balances']

        # Obtener órdenes abiertas
        open_orders = client.get_open_orders()

        return {
            'balances': balances,
            'open_orders': open_orders
        }
    except Exception as e:
        # Manejar errores en la conexión con Binance
        print(f"Error al obtener datos de Binance: {e}")
        return {
            'balances': [],
            'open_orders': []
        }
