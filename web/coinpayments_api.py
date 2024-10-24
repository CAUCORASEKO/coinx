# coinpayments_api.py
import requests
import hashlib
import hmac

class CoinPaymentsAPI:
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        self.base_url = 'https://www.coinpayments.net/api.php'

    def _create_signature(self, params):
        # Luo allekirjoitus API-pyyntöä varten käyttäen yksityistä avainta ja parametreja
        encoded_params = "&".join([f"{key}={value}" for key, value in params.items()])
        signature = hmac.new(self.private_key.encode(), encoded_params.encode(), hashlib.sha512).hexdigest()
        return signature

    def _post_request(self, command, params):
        # Päivitä parametrit API-pyyntöä varten
        params.update({
            'version': 1,
            'cmd': command,
            'key': self.public_key,
            'format': 'json'
        })

        headers = {
            'HMAC': self._create_signature(params)  # Lisää HMAC-allekirjoitus otsikoihin
        }

        # Lähetä POST-pyyntö CoinPayments API:lle ja palauta JSON-vastaus
        response = requests.post(self.base_url, data=params, headers=headers)
        return response.json()

    def get_basic_info(self):
        # Hae perusinformaatio käyttäen API-pyyntöä
        return self._post_request('get_basic_info', {})

    def create_transaction(self, amount, currency1, currency2, buyer_email, item_name):
        # Luo uusi transaktio määritetyillä parametreilla
        params = {
            'amount': amount,
            'currency1': currency1,
            'currency2': currency2,
            'buyer_email': buyer_email,
            'item_name': item_name
        }
        return self._post_request('create_transaction', params)
