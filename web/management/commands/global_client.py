from binance.client import Client as FuturesClient  # Futuuri-asiakas
import logging

# Määritä Binance API -avaimet
API_KEY = "Your API_KEY"
API_SECRET = "Your API_SECRET"

# Lokin konfigurointi
logger = logging.getLogger(__name__)

def get_global_client():
    """
    Palauttaa Binance-asiakkaan, joka on konfiguroitu kiinteillä avaimilla.
    """
    try:
        # Alustaa Binance-asiakkaan yleisillä tunnuksilla
        client = FuturesClient(API_KEY, API_SECRET)  # Futuuri-asiakas
        client.futures_ping()  # Testaa yhteys futuuripalvelimeen
        return client
    except Exception as e:
        logger.error(f"Error initializing Binance global client: {e}")
        return None
