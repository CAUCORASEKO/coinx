# binance_utils.py 

from binance.client import Client

def get_binance_data(api_key, api_secret):
    client = Client(api_key, api_secret)
    
    try:
        # Hae Spot-tilin saldot
        account_info = client.get_account()
        balances = account_info['balances']

        # Hae avoimet tilaukset
        open_orders = client.get_open_orders()

        return {
            'balances': balances,
            'open_orders': open_orders
        }
    except Exception as e:
        # Käsittele virheitä Binance-yhteydessä
        print(f"Error getting data from Binance: {e}")
        return {
            'balances': [],
            'open_orders': []
        }

