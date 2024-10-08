from binance.client import Client as FuturesClient  # Cliente de Futuros
import logging

# Config Binance API KEYs  
API_KEY = "Your API_KEY"
API_SECRET = "Your API_SECRET"

# Configuración del logger
logger = logging.getLogger(__name__)

def get_global_client():
    """
    Retorna un cliente de Binance configurado con claves fijas.
    """
    try:
        # Inicializar el cliente de Binance con las credenciales globales
        client = FuturesClient(API_KEY, API_SECRET)  # Cliente de Futuros
        client.futures_ping()  # Prueba de conexión al servidor de futuros
        return client
    except Exception as e:
        logger.error(f"Error al inicializar el cliente global de Binance: {e}")
        return None
