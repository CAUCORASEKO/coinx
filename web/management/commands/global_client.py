from binance.client import Client as FuturesClient  # Cliente de Futuros
import logging

# Configuración de las claves API de Binance (credenciales fijas)
API_KEY = "lSxB8SkFAKprXPA2zPkKg4PGVm6Ys9KKdK6Xbx9x5v3Nkq1t8s9bFrFXdh87yYxC"
API_SECRET = "Ddyd7kwyLzOmHxuirdgaWDsR6oymL6iQ3zdGivHGHxhwrq5C90SUaf0Sqgg3yTow"

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
