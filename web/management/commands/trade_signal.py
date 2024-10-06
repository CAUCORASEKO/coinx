import sys
import json
import os
import django
import pandas as pd
import numpy as np
import requests
import ta
import random
import logging
import threading
import time
from binance.exceptions import BinanceAPIException
from django.core.management.base import BaseCommand

# Definición de la clase para evitar mensajes duplicados
class NoDuplicateFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.last_log = None

    def filter(self, record):
        current_log = record.getMessage()
        if current_log != self.last_log:
            self.last_log = current_log
            return True
        return False

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuración del manejador y filtro para evitar duplicados
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(NoDuplicateFilter())
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Limpiar manejadores existentes y aplicar nuevo manejador
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(console_handler)

def log_single_instance(symbol, message, cache={}):
    if cache.get(symbol) != message:
        logger.info(message)
        cache[symbol] = message

# Asegúrate de que la ruta de importación esté correcta para obtener el cliente
from web.management.commands.global_client import get_global_client  # Importa el cliente global

# Establecer la variable DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')  # Ajusta con tu proyecto

# Inicializa Django
try:
    django.setup()
except Exception as e:
    logger.error(f"Error inicializando Django: {e}")
    sys.exit(1)

# Obtener el cliente de Binance
client = get_global_client()
if client is None:
    logger.error("No se pudo inicializar el cliente global de Binance. Abortando.")
    sys.exit(1)

# Aquí encapsulamos la lógica de Django Command
class Command(BaseCommand):
    help = 'Inicia el análisis de trading avanzado'

    def handle(self, *args, **options):
        logger.info("Iniciando el análisis de trading desde el comando de Django...")
        # Crear y empezar el hilo sin detener el proceso principal
        thread = threading.Thread(target=perform_trade_analysis)
        thread.start()


# Configuración centralizada
KLINE_INTERVAL = '1h'
KLINE_LIMIT = 100
ORDER_BOOK_LIMIT = 100


# Obtener el cliente de Binance desde global_client.py


if client is None:
    logger.error("No se pudo inicializar el cliente global de Binance. Abortando.")
    sys.exit(1)  # Termina el script si no hay cliente


# Función para obtener información de la cuenta
def fetch_futures_account(client, retries=3, delay=5):
    last_exception = None  # Almacena la última excepción
    for attempt in range(retries):
        try:
            response = client.futures_account()
            logger.info(f"Datos de la cuenta: {response}")
            if isinstance(response, dict):
                return response
        except (BinanceAPIException, Exception) as e:
            last_exception = e
            time.sleep(delay)
    
    # Log solo si se agotaron todos los reintentos
    logger.error(f"Error durante la solicitud API: {last_exception}")
    logger.error("Se excedió el máximo de reintentos para la API de Binance.")
    return None



# Función para obtener información de la cuenta
def get_account_info(client, retries=3, delay=5):
    """
    Obtiene información de la cuenta de futuros de Binance.
    """
    for attempt in range(retries):
        try:
            response = client.futures_account()
            logger.info(f"Datos de la cuenta: {response}")
            return response
        except (BinanceAPIException, Exception) as e:
            logger.error(f"Error durante la solicitud API: {e}")
            time.sleep(delay)
    logger.error("Se excedió el máximo de reintentos para la API de Binance.")
    return None



def calculate_fibonacci_levels(high, low):
    """
    Calcula los niveles de Fibonacci entre el máximo y el mínimo.
    """
    levels = {
        '0.236': high - (high - low) * 0.236,
        '0.382': high - (high - low) * 0.382,
        '0.5': (high + low) / 2,
        '0.618': high - (high - low) * 0.618,
        '0.786': high - (high - low) * 0.786,
        '1.0': high,
        '1.272': high + (high - low) * 1.272,
        '1.618': high + (high - low) * 1.618,
        '2.618': high + (high - low) * 2.618,
        '4.236': high + (high - low) * 4.236
    }
    # Convertir a float nativo para evitar problemas de compatibilidad
    levels = {k: float(v) for k, v in levels.items()}
    return levels




market_cap_cache = {}
market_cap_last_fetch = {}

def get_market_cap_from_coingecko(crypto_id, cache_duration=3600, retries=3, delay=5):
    """
    Obtiene el Market Cap desde CoinGecko con caché y reintentos.
    """
    current_time = time.time()

    # Uso de caché si el tiempo es reciente
    if crypto_id in market_cap_cache and (current_time - market_cap_last_fetch[crypto_id] < cache_duration):
        logger.info(f"Usando caché para Market Cap de {crypto_id}")
        return market_cap_cache[crypto_id]

    # Intento de obtener datos de CoinGecko
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                market_cap = data['market_data']['market_cap']['usd']

                # Actualizar caché
                market_cap_cache[crypto_id] = market_cap
                market_cap_last_fetch[crypto_id] = current_time
                return market_cap
            else:
                logger.error(f"Error {response.status_code} en CoinGecko para {crypto_id}. Reintentando...")
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Error al obtener Market Cap para {crypto_id}: {e}. Reintentando en {delay} segundos.")
            time.sleep(delay)

    logger.error(f"No se pudo obtener Market Cap de {crypto_id} después de {retries} intentos.")
    return None


    
    
    



def analyze_btc_market_cap(btc_data):
    """
    Realiza el análisis de BTC y añade el Market Cap y otros indicadores técnicos al resultado.
    """
    # Obtener el Market Cap de BTC desde CoinGecko
    btc_market_cap = get_market_cap_from_coingecko('bitcoin')
    if btc_market_cap:
        logger.info(f"Market Cap de BTC: ${btc_market_cap:,.2f}")
    else:
        logger.warning("No se pudo obtener el Market Cap de BTC.")

    # Validación para columnas requeridas
    required_columns = {'high', 'low', 'close', 'volume'}
    if not required_columns.issubset(btc_data.columns):
        missing_cols = required_columns - set(btc_data.columns)
        logger.error(f"Error: Faltan columnas importantes en el DataFrame de BTC: {missing_cols}")
        return None

    # Realizar el análisis de BTC (indicadores técnicos)
    # 1. VWAP
    btc_data['vwap'] = calculate_vwap(btc_data)

    # 2. ATR (Average True Range)
    btc_data['atr'] = ta.volatility.average_true_range(btc_data['high'], btc_data['low'], btc_data['close']).fillna(0)

    # 3. EMAs
    btc_data['ema_50'] = ta.trend.ema_indicator(btc_data['close'], window=50).fillna(method='bfill')
    btc_data['ema_200'] = ta.trend.ema_indicator(btc_data['close'], window=200).fillna(method='bfill')

    # 4. RSI (Relative Strength Index)
    btc_data['rsi'] = ta.momentum.rsi(btc_data['close']).fillna(50)

    # 5. MFI (Money Flow Index)
    btc_data['mfi'] = ta.volume.money_flow_index(
        btc_data['high'], btc_data['low'], btc_data['close'], btc_data['volume']
    ).fillna(50)

    # 6. MACD (Moving Average Convergence Divergence)
    btc_data['macd'] = ta.trend.macd_diff(btc_data['close']).fillna(0)

    # 7. Ichimoku Indicator
    btc_data = calculate_ichimoku(btc_data).fillna(method='bfill')

    # 8. Perfil de Volumen
    try:
        volume_profile = calculate_volume_profile_with_nodes(btc_data)
        if volume_profile is not None and not volume_profile.empty:
            logger.info(f"Perfil de Volumen: {volume_profile}")
        else:
            logger.warning("El perfil de volumen está vacío.")
    except Exception as e:
        logger.error(f"Error al calcular el perfil de volumen: {e}")

    # 9. Niveles de Fibonacci
    high, low = btc_data['high'].max(), btc_data['low'].min()
    fibonacci_levels = calculate_fibonacci_levels(high, low)
    for level, value in fibonacci_levels.items():
        btc_data[f'fibonacci_{level}'] = value

    logger.info(f"Niveles de Fibonacci calculados: {fibonacci_levels}")
    return btc_data



def analyze_random_symbol_market_cap(symbol, data):
    """
    Realiza el análisis para un símbolo aleatorio, pero solo incluye el Market Cap para BTC.
    """
    # Solo obtener el Market Cap si el símbolo es BTC
    if symbol == 'BTCUSDT':
        crypto_base = 'bitcoin'  # Solo en el caso de BTC obtener el market cap
        market_cap = get_market_cap_from_coingecko(crypto_base)
        
        if market_cap:
            logger.info(f"Market Cap de {crypto_base.upper()}: ${market_cap:,.2f}")
        else:
            logger.error(f"No se pudo obtener el Market Cap para {crypto_base.upper()}.")
    else:
        logger.info(f"Saltando la obtención del Market Cap para {symbol}")

    # Realizar el análisis de indicadores técnicos para el símbolo
    data = calculate_technical_indicators(data)
    
    return data

   
    
    

def get_order_book(symbol, retries=3, delay=5):
    """
    Obtiene el libro de órdenes con reintentos en caso de error.
    """
    for attempt in range(retries):
        try:
            order_book = client.futures_order_book(symbol=symbol, limit=ORDER_BOOK_LIMIT)
            bids = [(float(bid[0]), float(bid[1])) for bid in order_book['bids']]
            asks = [(float(ask[0]), float(ask[1])) for ask in order_book['asks']]

            # Confirmación de datos válidos
            if bids and asks:
                return bids, asks
            else:
                logger.error(f"Bids o asks vacíos para {symbol}. Reintentando...")

        except Exception as e:
            logger.error(f"Error al obtener el libro de órdenes para {symbol}: {e}. Reintentando en {delay} segundos.")
            time.sleep(delay)

    logger.error(f"Error: No se pudo obtener el libro de órdenes para {symbol} después de {retries} intentos.")
    return [], []



def calculate_weighted_average_price(levels):
    total_volume = sum(size for _, size in levels)
    if total_volume == 0:
        logger.error("El volumen total es 0, no se puede calcular el precio ponderado.")
        return None
    weighted_avg_price = sum(price * size for price, size in levels)
    if total_volume > 0:
        weighted_avg_price /= total_volume
    return weighted_avg_price



def is_volume_significant(orders, min_volume=1000):  # Ajusta el volumen mínimo según tus necesidades
    total_volume = sum(quantity for _, quantity in orders)
    return total_volume >= min_volume

def get_weighted_prices_from_order_book(symbol, retries=3):
    """
    Obtiene los precios de compra y venta ponderados del libro de órdenes para un símbolo dado.
    """
    for _ in range(retries):
        bids, asks = get_order_book(symbol)
        
        if not bids or not asks:
            logger.error(f"Error: bids o asks están vacíos para el símbolo {symbol}. Reintentando...")
            time.sleep(2)
            continue  # Reintenta si los datos están vacíos

        # Verificar si el volumen es significativo
        if not is_volume_significant(bids) or not is_volume_significant(asks):
            logger.warning(f"Volumen insuficiente para {symbol}. Reintentando...")
            time.sleep(2)
            continue

        # Calcula los precios ponderados de compra y venta
        weighted_buy_price = calculate_weighted_average_price(bids)
        weighted_sell_price = calculate_weighted_average_price(asks)

        # Verifica si se pudieron calcular los precios ponderados
        if weighted_buy_price is None or weighted_sell_price is None:
            logger.error(f"No se pudieron calcular los precios ponderados para {symbol}. Reintentando...")
            time.sleep(2)
            continue  # Reintenta si no se pueden calcular

        logger.info(f"Precios ponderados calculados para {symbol} -> Compra: {weighted_buy_price:.2f}, Venta: {weighted_sell_price:.2f}")
        return weighted_buy_price, weighted_sell_price

    # Si no se pueden obtener los precios después de los reintentos, devuelve None
    logger.error(f"Error: No se pudo obtener precios ponderados para {symbol} después de {retries} intentos.")
    return None, None




def calculate_force(bids, asks):
    volume_bids = sum(quantity for _, quantity in bids)
    volume_asks = sum(quantity for _, quantity in asks)
    total_volume = volume_bids + volume_asks
    
    if total_volume == 0:
        return 0.5, 0.5
    
    force_bulls = np.log1p(volume_bids) / np.log1p(total_volume)
    force_bears = np.log1p(volume_asks) / np.log1p(total_volume)
    
    return force_bulls, force_bears

#def calculate_weighted_average_price(levels):
#   total_volume = sum(size for price, size in levels)
#   if total_volume == 0:
#        return None
#    weighted_avg_price = sum(price * size for price, size in levels) / total_volume
#    return weighted_avg_price

def identify_key_levels(bids, asks):
    support = calculate_weighted_average_price(bids)
    resistance = calculate_weighted_average_price(asks)
    return support, resistance



def calculate_vwap(data):
    return ta.volume.volume_weighted_average_price(data['high'], data['low'], data['close'], data['volume'])





def calculate_ichimoku(data):
    ichimoku = ta.trend.IchimokuIndicator(data['high'], data['low'], window1=9, window2=26, window3=52)
    data['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
    data['kijun_sen'] = ichimoku.ichimoku_base_line()
    data['senkou_span_a'] = ichimoku.ichimoku_a()
    data['senkou_span_b'] = ichimoku.ichimoku_b()
    data['chikou_span'] = data['close'].shift(-26)  # Añadimos la línea Chikou Span (desplazada 26 períodos)
    
    # Detectar cruces de Tenkan-sen y Kijun-sen
    data['ichimoku_cross'] = np.where(
        (data['tenkan_sen'].shift(1) < data['kijun_sen'].shift(1)) & (data['tenkan_sen'] > data['kijun_sen']), 
        'Bullish Cross', 
        np.where((data['tenkan_sen'].shift(1) > data['kijun_sen'].shift(1)) & (data['tenkan_sen'] < data['kijun_sen']), 
                 'Bearish Cross', 
                 'No Cross')
    )
    return data

def calculate_time_cycles(data, anchor_point, cycle_length=26):
    """
    Calcula los ciclos de tiempo proyectando líneas desde el punto de anclaje (anchor_point) usando el ciclo Ichimoku.
    """
    time_cycles = []
    for i in range(1, 5):  # Proyecta los próximos 4 ciclos
        cycle = anchor_point + (cycle_length * i)
        # Puedes agregar alguna operación usando 'data' aquí si es relevante
        if data is not None and len(data) > 0:  # Por ejemplo, usando la longitud de los datos
            cycle += len(data)  # Ajustar el ciclo basado en los datos, si es necesario.
        time_cycles.append(cycle)
    
    return time_cycles



def detect_wave_patterns(data):
    """
    Detecta patrones de ondas simples (I, V, N) y complejas (P, Y, W) en los datos de precios.
    """
    waves = {}
    
    # Simple Wave: I, V, N
    waves['I_wave'] = (data['close'].iloc[-1] - data['low'].min()) / data['low'].min()
    waves['V_wave'] = (data['high'].max() - data['low'].min()) / data['low'].min()
    waves['N_wave'] = waves['V_wave'] + waves['I_wave']  # Patrón simple
    
    # Complex Waves: P, Y, W (se pueden agregar cálculos más complejos)
    waves['P_wave'] = None  # Placeholder para lógica más avanzada
    
    return waves


def calculate_price_targets(data, wave_type='N'):
    """
    Calcula los objetivos de precio basados en el tipo de onda.
    """
    if wave_type == 'N':
        v_target = data['close'].max() + (data['close'].max() - data['low'].min())  # Ejemplo simple para la onda N
        e_target = v_target * 1.618  # Usando un múltiplo de Fibonacci para proyección adicional
        nt_target = e_target * 1.272  # Proyección NT
    
    return v_target, e_target, nt_target


def monitor_unusual_volume(data, volume_threshold=1.5):
    """
    Detecta picos de volumen inusual comparando con promedios a corto, medio y largo plazo.
    Devuelve True si se detecta un volumen inusual.
    """
    short_term_avg_volume = data['volume'].rolling(window=5).mean().iloc[-1]
    mid_term_avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
    long_term_avg_volume = data['volume'].rolling(window=50).mean().iloc[-1]
    last_volume = data['volume'].iloc[-1]
    
    if (last_volume > mid_term_avg_volume * volume_threshold and last_volume > short_term_avg_volume * 1.2
        and last_volume > long_term_avg_volume * 1.1):  # Agregar el chequeo con long_term_avg_volume
        logger.info(f"Volumen inusual detectado: {last_volume}.")
        return True
    return False




def detect_liquidity_voids(bids, asks, threshold=0.05):
    """
    Detecta vacíos de liquidez en el libro de órdenes basado en el spread entre las órdenes de compra y venta.
    Devuelve True si se detecta un vacío de liquidez.
    """
    if len(bids) < 2 or len(asks) < 2:
        return False
    
    bid_ask_spread = asks[0][0] - bids[0][0]
    mid_price = (asks[0][0] + bids[0][0]) / 2
    
    if bid_ask_spread / mid_price > threshold:
        logger.info(f"Vacío de liquidez detectado. Spread: {bid_ask_spread:.4f}")
        return True
    
    return False



def detect_stop_hunting(price, support, resistance, bids, asks, spread_threshold=0.03, data=None, interval=KLINE_INTERVAL, limit=KLINE_LIMIT):
    """
    Detecta patrones de caza de stop losses en base a movimientos rápidos en niveles clave y volatilidad reciente.
    Devuelve True si se detecta posible caza de stop losses.
    """
    try:
        # Calcular el spread entre las órdenes de compra y venta
        spread = asks[0][0] - bids[0][0]
        
        # Calcular ATR a partir de los datos históricos si están disponibles
        if data is not None:
            # Ajustar el cálculo de ATR en función del intervalo
            atr_factor = 1 if interval == '1h' else 2  # Ejemplo de ajuste basado en intervalos
            actual_limit = min(len(data), limit)
            atr = ta.volatility.average_true_range(
                data['high'].iloc[-actual_limit:], 
                data['low'].iloc[-actual_limit:], 
                data['close'].iloc[-actual_limit:]
            ).iloc[-1] * atr_factor
        else:
            # Si no hay datos históricos, estimar ATR en base a soporte y resistencia
            atr = (resistance - support) / 10

        # Condiciones de posible caza de stop losses
        if (
            (abs(price - support) / support < spread_threshold or abs(price - resistance) / resistance < spread_threshold) 
            and spread > atr
        ):
            logger.info(f"Posible caza de stop losses detectada. Spread: {spread:.4f}, ATR: {atr:.4f}")
            return True

        return False

    except Exception as e:
        logger.error(f"Error en detect_stop_hunting: {e}")
        return False




# Simulación de obtener datos de volatilidad implícita
def get_volatility_data():
    """
    Simula la obtención de datos de volatilidad implícita para BTC.
    """
    # Este bloque debe integrarse con una API de opciones como Skew, Deribit, etc.
    return {
        'volatility': 0.65,  # Ejemplo de volatilidad implícita
        'skew': 0.10         # Ejemplo de sesgo entre opciones call/put
    }

# Analizar los datos de volatilidad implícita
vol_data = get_volatility_data()
logger.info(f"Volatilidad implícita: {vol_data['volatility']:.2f}, Skew: {vol_data['skew']:.2f}")

# Análisis basado en la volatilidad implícita (sin enviar alerta a Telegram)
if vol_data['volatility'] > 0.7:
    # Ajustar estrategias o tener en cuenta este dato para el análisis de BTC sin enviar alerta.
    logger.info(f"Volatilidad implícita alta detectada ({vol_data['volatility']:.2f}). Posible gran movimiento en BTC.")


def analyze_volatility_impact(volatility_data, historical_data):
    """
    Analiza la volatilidad implícita y la compara con la volatilidad histórica.
    Devuelve True si la volatilidad implícita es significativamente mayor a la histórica.
    """
    historical_volatility = historical_data['close'].pct_change().rolling(window=20).std().iloc[-1] * np.sqrt(365)
    implied_volatility = volatility_data.get('volatility', 0)
    
    logger.info(f"Volatilidad implícita: {implied_volatility:.2f}, Volatilidad histórica: {historical_volatility:.2f}")
    
    if implied_volatility > historical_volatility * 1.5:
        logger.info("Volatilidad implícita muy superior a la volatilidad histórica, posible gran movimiento.")
        return True
    return False





def calculate_btc_indicators(btc_data):
    # 1. VWAP
    btc_data['vwap'] = calculate_vwap(btc_data)
    
    # 2. ATR (Average True Range)
    btc_data['atr'] = ta.volatility.average_true_range(btc_data['high'], btc_data['low'], btc_data['close'])
    
    # 3. EMAs
    btc_data['ema_50'] = ta.trend.ema_indicator(btc_data['close'], window=50)
    btc_data['ema_200'] = ta.trend.ema_indicator(btc_data['close'], window=200)
    
    # 4. RSI (Relative Strength Index)
    btc_data['rsi'] = ta.momentum.rsi(btc_data['close'])
    
    # 5. MFI (Money Flow Index)
    btc_data['mfi'] = ta.volume.money_flow_index(btc_data['high'], btc_data['low'], btc_data['close'], btc_data['volume'])
    
    # 6. MACD (Moving Average Convergence Divergence)
    btc_data['macd'] = ta.trend.macd_diff(btc_data['close'])

    # 7. Ichimoku Indicator
    btc_data = calculate_ichimoku(btc_data)

    # 8. Perfilador de Volumen
    volume_profile = calculate_volume_profile_with_nodes(btc_data)
    logger.info(f"Perfil de Volumen: {volume_profile}")

    # 9. Fibonacci (Retrocesos y Extensiones)
    high = btc_data['high'].max()  # Obtener el valor máximo
    low = btc_data['low'].min()    # Obtener el valor mínimo
    fibonacci_levels = calculate_fibonacci_levels(high, low)  # Asegurarse de pasar ambos valores
    logger.info(f"Niveles de Fibonacci calculados: {fibonacci_levels}")

    # Almacenar los niveles de Fibonacci en el DataFrame para posibles referencias
    for level, value in fibonacci_levels.items():
        btc_data[f'fibonacci_{level}'] = value

    return btc_data




def get_market_sentiment():
    try:
        # Obtener las estadísticas del mercado de futuros de BTC
        btc_stats = client.futures_ticker(symbol='BTCUSDT')
        price_change_percent = float(btc_stats['priceChangePercent'])
        volume = float(btc_stats['volume'])
        open_interest = float(btc_stats['openInterest'])
        
        # Obtener el Market Cap de BTC
        btc_market_cap = get_market_cap_from_coingecko('bitcoin')

        if btc_market_cap:
            logger.info(f"Market Cap de BTC: ${btc_market_cap:,.2f}")
            # Ajustar el cálculo del sentimiento usando el Market Cap
            sentiment_score = (price_change_percent * volume * open_interest * btc_market_cap) / 1000000000000  # Ajustado para el tamaño del Market Cap
            sentiment = 'Bullish' if price_change_percent > 0 else 'Bearish' if price_change_percent < 0 else 'Neutral'
            return sentiment, sentiment_score
        else:
            logger.error("No se pudo obtener el Market Cap de BTC. Usando cálculo básico.")
            sentiment_score = (price_change_percent * volume * open_interest) / 10000  # Cálculo sin el Market Cap
            sentiment = 'Bullish' if price_change_percent > 0 else 'Bearish' if price_change_percent < 0 else 'Neutral'
            return sentiment, sentiment_score
    except Exception as e:
        logger.error(f"Error al obtener el sentimiento del mercado: {e}")
        return None, 0


    

def calculate_combined_force(bids, asks, data):
    """
    Calcula la fuerza combinada de toros y osos, ponderada con EMAs y MACD.
    """
    volume_bids = sum(quantity for _, quantity in bids)
    volume_asks = sum(quantity for _, quantity in asks)
    total_volume = volume_bids + volume_asks
    
    if total_volume == 0:
        return 0.5, 0.5  # Neutral
    
    force_bulls = np.log1p(volume_bids) / np.log1p(total_volume)
    force_bears = np.log1p(volume_asks) / np.log1p(total_volume)
    
    # Ponderar con la tendencia de las EMAs y el MACD
    ema_trend = 1 if data['ema_50'].iloc[-1] > data['ema_200'].iloc[-1] else -1
    macd_trend = 1 if data['macd'].iloc[-1] > 0 else -1
    
    combined_force_bulls = force_bulls * 0.5 + ema_trend * 0.25 + macd_trend * 0.25
    combined_force_bears = force_bears * 0.5 + (1 - ema_trend) * 0.25 + (1 - macd_trend) * 0.25
    
    return combined_force_bulls, combined_force_bears



def calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d):
    logger.info(f"Calculando entry, stop loss y take profit para {symbol}")

    if data.empty:
        logger.error(f"Error: Data vacío para {symbol}")
        return None, None

    if 'ema_50' not in data.columns or 'ema_200' not in data.columns:
        logger.error(f"Error: Faltan columnas EMA en {symbol}")
        return None, None

    # Obtener el libro de órdenes
    bids, asks = get_order_book(symbol)
    if not bids or not asks:
        logger.error(f"Error: bids o asks están vacíos para el símbolo {symbol}")
        return None, None

    # Identificar soporte y resistencia
    support, resistance = identify_key_levels(bids, asks)
    if support is None or resistance is None:
        logger.error(f"Error: Soporte o resistencia nulos para {symbol}")
        return None, None

    logger.info(f"Identificados desde el libro de órdenes -> Soporte: {support:.2f}, Resistencia: {resistance:.2f}")

    # Obtener los precios ponderados
    weighted_buy_price, weighted_sell_price = get_weighted_prices_from_order_book(symbol)
    if weighted_buy_price is None or weighted_sell_price is None:
        logger.error(f"No se pudieron obtener precios ponderados para {symbol}, omitiendo análisis.")
        return None, None

    # Calcular indicadores técnicos
    data = calculate_technical_indicators(data)
    if data is None:
        logger.error(f"Error: No se pudieron calcular los indicadores técnicos para {symbol}")
        return None, None

    # Calcular la fuerza combinada
    force_bulls, force_bears = calculate_combined_force(bids, asks, data)
    logger.info(f"Fuerza combinada de toros: {force_bulls:.2f}, Fuerza combinada de osos: {force_bears:.2f}")

    # Verificar las tendencias de BTC en diferentes temporalidades
    btc_trend_1h = "up" if btc_data_1h['ema_50'].iloc[-1] > btc_data_1h['ema_200'].iloc[-1] else "down"
    btc_trend_1d = "up" if btc_data_1d['ema_50'].iloc[-1] > btc_data_1d['ema_200'].iloc[-1] else "down"
    logger.info(f"Tendencia de BTC (1h): {btc_trend_1h}, Tendencia de BTC (1d): {btc_trend_1d}")

    # Verificar la tendencia del activo
    trend = "up" if data['ema_50'].iloc[-1] > data['ema_200'].iloc[-1] else "down"
    logger.info(f"Tendencia para {symbol}: {trend}")

    
    # Inicializar variables para evitar errores de no asignación
    entry_long = entry_short = None
    entry_long_2 = entry_short_2 = None
    quality_long = quality_short = None
    stop_loss_long = stop_loss_short = None
    take_profits_long = take_profits_short = None
    signal_strength_long = signal_strength_short = None

    # **Buscar oportunidades en condiciones de sobrecompra/sobreventa**
    if data['rsi'].iloc[-1] > 80 or data['mfi'].iloc[-1] > 80:
        logger.info(f"Oportunidad detectada en condiciones de sobrecompra para {symbol}. Buscando entradas cortas.")
        # Se puede ajustar la lógica para priorizar entradas cortas en estas condiciones
        entry_short, quality_short = find_entry_point(symbol, data, bids, asks, "down", support, resistance)
    
    if data['rsi'].iloc[-1] < 20 or data['mfi'].iloc[-1] < 20:
        logger.info(f"Oportunidad detectada en condiciones de sobreventa para {symbol}. Buscando entradas largas.")
        # Se puede ajustar la lógica para priorizar entradas largas en estas condiciones
        entry_long, quality_long = find_entry_point(symbol, data, bids, asks, "up", support, resistance)

    # Si no se detectaron condiciones de sobrecompra o sobreventa, se buscan oportunidades regulares
    if not entry_long and not entry_short:
        # Puntos de entrada y calidad
        entry_long, quality_long = find_entry_point(symbol, data, bids, asks, "up", support, resistance)
        entry_short, quality_short = find_entry_point(symbol, data, bids, asks, "down", support, resistance)

    # Si quieres usar quality_long y quality_short
    if quality_long is not None:
        logger.info(f"Calidad de Entry Point Long: {quality_long}")
    
    if quality_short is not None:
        logger.info(f"Calidad de Entry Point Short: {quality_short}")

    # Procesar las entradas si se encuentran
    if entry_long is not None:
        entry_long, entry_long_2, stop_loss_long, take_profits_long, signal_strength_long = process_entry(entry_long, data, "up")
    else:
        logger.info(f"No se encontró un punto de entrada long válido para {symbol}")

    if entry_short is not None:
        entry_short, entry_short_2, stop_loss_short, take_profits_short, signal_strength_short = process_entry(entry_short, data, "down")
    else:
        logger.info(f"No se encontró un punto de entrada short válido para {symbol}")

    # Verificar que las entradas existan antes de proceder a preparar el retorno
    return prepare_return(entry_long, entry_long_2, stop_loss_long, take_profits_long, signal_strength_long, "Long") if entry_long else None, \
           prepare_return(entry_short, entry_short_2, stop_loss_short, take_profits_short, signal_strength_short, "Short") if entry_short else None




def calculate_technical_indicators(data):
    try:
        # Asegurarse de que las columnas necesarias existen
        required_columns = {'high', 'low', 'close', 'volume'}
        if not required_columns.issubset(data.columns):
            missing_cols = required_columns - set(data.columns)
            logger.error(f"Error: Faltan columnas importantes en el DataFrame: {missing_cols}")
            return None

        # Intento para calcular ATR directamente
        data['atr'] = ta.volatility.average_true_range(data['high'], data['low'], data['close'])
        
        # Verificación después del primer intento
        if data['atr'].isnull().all():
            logger.warning("ATR no pudo ser calculado en el primer intento. Aplicando tratamiento de datos.")

            # Tratamiento de datos si el cálculo de ATR falla
            data = handle_null_values(data, "ATR Calculation")  # Llenar nulos y eliminar duplicados si existen
            data['atr'] = ta.volatility.average_true_range(data['high'], data['low'], data['close'])  # Recalcular ATR
            
            # Si aún no se puede calcular, forzar el relleno
            if data['atr'].isnull().all():
                data['atr'].fillna(data['atr'].rolling(window=2, min_periods=1).mean(), inplace=True)
                logger.info("ATR forzado mediante media móvil.")

        # Calcular el resto de los indicadores técnicos solo si ATR fue calculado
        data['vwap'] = calculate_vwap(data)
        data['ema_50'] = ta.trend.ema_indicator(data['close'], window=50)
        data['ema_200'] = ta.trend.ema_indicator(data['close'], window=200)
        data['rsi'] = ta.momentum.rsi(data['close'])
        data['macd'] = ta.trend.macd_diff(data['close'])
        data['mfi'] = ta.volume.money_flow_index(data['high'], data['low'], data['close'], data['volume'])

        # Calcular niveles de Fibonacci e Ichimoku
        high, low = data['high'].max(), data['low'].min()
        fibonacci_levels = calculate_fibonacci_levels(high, low)
        for level, value in fibonacci_levels.items():
            data[f'fibonacci_{level}'] = value
        data = calculate_ichimoku(data)

    except Exception as e:
        logger.error(f"Error crítico al calcular los indicadores técnicos: {e}")
        return None

    # Mensaje final para confirmar el cálculo de ATR
    if data['atr'].isnull().all():
        logger.error("No se pudo calcular ATR incluso después de múltiples intentos.")
        return None
    else:
        logger.info("ATR calculado exitosamente.")

    return data





def calculate_atr(data):
    """
    Calcula el ATR si no existe en el DataFrame y lo añade.
    """
    if 'atr' not in data.columns:
        try:
            data['atr'] = ta.volatility.average_true_range(data['high'], data['low'], data['close'])
        except Exception as e:
            logger.error(f"Error al calcular ATR: {e}")
            return None
    return data['atr']





def evaluate_entry_quality(data):
    # Calcular `dr` basado en la estrategia
    b1 = 2 if data['rsi'].iloc[-1] < 20 else 1 if data['rsi'].iloc[-1] < 30 else -2 if data['rsi'].iloc[-1] > 80 else -1 if data['rsi'].iloc[-1] > 70 else 0
    b2 = 2 if data['stoch'].iloc[-1] < 20 else 1 if data['stoch'].iloc[-1] < 30 else -2 if data['stoch'].iloc[-1] > 80 else -1 if data['stoch'].iloc[-1] > 70 else 0
    b3 = 1 if data['close'].iloc[-1] > data['ema_20'].iloc[-1] else -1
    b4 = 1 if data['ema_20'].iloc[-1] > data['ema_20'].iloc[-2] else -1

    # Puntuación total
    sm = b1 + b2 + b3 + b4
    dr = 2 if sm > 3 else 1 if sm > 1 else -2 if sm < -3 else -1 if sm < -1 else 0

    # Determinar el color de alerta
    decision_color = "lime" if dr > 1 else "green" if dr > 0 else "darkRed" if dr < -1 else "red" if dr < 0 else "blue"
    
    # Calidad basada en la puntuación de `dr`
    quality = 7.5 if dr > 0 else 5.0 if dr < 0 else 4.0

    return quality, decision_color



def calculate_volume_profile_with_nodes(data, num_bins=20, volume_threshold=0.05):
    # Asegúrate de que 'atr' esté calculado
    if 'atr' not in data.columns or data['atr'].isnull().all():
        data['atr'] = calculate_atr(data)
        if data['atr'].isnull().all():
            logger.error("No se pudo calcular ATR en calculate_volume_profile_with_nodes. Terminando función.")
            return pd.DataFrame()  # Devolvemos un DataFrame vacío en caso de error

    # Definir los límites de los bins
    price_min = data['close'].min()
    price_max = data['close'].max()
    bins = np.linspace(price_min, price_max, num_bins)

    # Crear `price_bin` y asignar como `str`
    data['price_bin'] = pd.cut(data['close'], bins=bins, include_lowest=True, duplicates='drop').astype(str)

    # Agrupar y calcular el perfil de volumen
    volume_profile = data.groupby('price_bin')['volume'].sum().reset_index()
    total_volume = volume_profile['volume'].sum()
    
    # Calcula el porcentaje de volumen y determina HVN y LVN
    volume_profile['volume_percent'] = volume_profile['volume'] / total_volume
    volume_threshold_adjusted = volume_threshold * (1 + data['atr'].iloc[-1] / data['close'].mean())
    volume_profile['HVN'] = volume_profile['volume_percent'] > volume_threshold_adjusted
    volume_profile['LVN'] = volume_profile['volume_percent'] < (volume_threshold_adjusted / 2)

    # Calcular el precio promedio para HVN y LVN usando el valor medio de cada bin
    hvn_price = (
        volume_profile.loc[volume_profile['HVN'], 'price_bin']
        .apply(lambda x: (float(x[1:-1].split(', ')[0]) + float(x[1:-1].split(', ')[1])) / 2 if x is not None else None)
        .dropna()
        .mean()
    )
    lvn_price = (
        volume_profile.loc[volume_profile['LVN'], 'price_bin']
        .apply(lambda x: (float(x[1:-1].split(', ')[0]) + float(x[1:-1].split(', ')[1])) / 2 if x is not None else None)
        .dropna()
        .mean()
    )

    return hvn_price, lvn_price, volume_profile if isinstance(volume_profile, pd.DataFrame) else pd.DataFrame()





# Crea un caché global para almacenar el último mensaje registrado para cada símbolo
volume_profile_cache = {}

def log_volume_profile(symbol, hvn_price, lvn_price):
    """
    Registra el perfil de volumen solo si el mensaje no ha sido registrado previamente en este ciclo.
    """
    message = f"Perfil de Volumen calculado para {symbol}. HVN: {hvn_price}, LVN: {lvn_price}"

    # Verifica si el mensaje es el mismo que el último registrado para este símbolo
    if volume_profile_cache.get(symbol) != message:
        logger.info(message)  # Solo registra si el mensaje es nuevo
        volume_profile_cache[symbol] = message  # Actualiza el caché con el nuevo mensaje

def log_neutral_condition(symbol):
    """
    Registra las condiciones neutrales para un símbolo solo si no ha sido registrado previamente.
    """
    message = f"Condiciones neutrales para {symbol}, omitiendo señal."

    if volume_profile_cache.get(symbol) != message:
        logger.info(message)
        volume_profile_cache[symbol] = message




def find_entry_point(symbol, data, bids, asks, trend, support, resistance):
    logger.info(f"Buscando puntos de entrada {trend} para {symbol}")

    # Obtener los precios ponderados del libro de órdenes
    weighted_buy_price, weighted_sell_price = get_weighted_prices_from_order_book(symbol)

    # Calcular el ATR para ajustar los puntos de entrada según la volatilidad
    atr = data['atr'].iloc[-1]

    # Calcular la fuerza de los compradores (bids) y vendedores (asks)
    force_bulls, force_bears = calculate_force(bids, asks)

    # Ajustar puntos de entrada basado en la fuerza del mercado
    if trend == "up" and force_bulls > 0.55:  # Si la fuerza de los compradores es alta
        entry_point_1 = max(support, weighted_buy_price - atr)  # Ajuste de entrada con soporte y ATR
        entry_point_2 = max(support, weighted_buy_price - (atr * 1.5))  # Mayor volatilidad ajustada
    elif trend == "down" and force_bears > 0.55:  # Si la fuerza de los vendedores es alta
        entry_point_1 = min(resistance, weighted_sell_price + atr)  # Ajuste con resistencia y ATR
        entry_point_2 = min(resistance, weighted_sell_price + (atr * 1.5))  # Mayor volatilidad
    else:
        logger.info(f"La fuerza de mercado no soporta la entrada en {symbol}. Omisión del trade.")
        return None, None

    logger.info(f"Puntos ajustados de entrada - Entry Point 1: {entry_point_1:.4f}, Entry Point 2: {entry_point_2:.4f}")

    # Calcular el perfil de volumen con nodos HVN/LVN
    volume_profile = calculate_volume_profile_with_nodes(data)

    # Evaluar la calidad del punto de entrada usando el perfil de volumen
    def entry_quality(price):
        return evaluate_entry_quality(
            trend=trend,
            price=price,
            vwap=data['vwap'].iloc[-1], 
            atr=atr, 
            rsi=data['rsi'].iloc[-1], 
            macd=data['macd'].iloc[-1], 
            ema_50=data['ema_50'].iloc[-1],
            tenkan_sen=data['tenkan_sen'].iloc[-1], 
            kijun_sen=data['kijun_sen'].iloc[-1], 
            senkou_span_a=data['senkou_span_a'].iloc[-1], 
            senkou_span_b=data['senkou_span_b'].iloc[-1], 
            volume_profile=volume_profile  # Integración del perfil de volumen
        )

    # Evaluar la calidad de los puntos de entrada
    quality_entry_point_1 = entry_quality(entry_point_1)
    quality_entry_point_2 = entry_quality(entry_point_2)

    logger.info(f"Calidad de Entry Point 1: {quality_entry_point_1:.2f}, Calidad de Entry Point 2: {quality_entry_point_2:.2f}")

    # Ajustar el umbral de calidad en función de la volatilidad
    quality_threshold = 4.0 if atr < data['close'].mean() * 0.01 else 3.5

    # Filtrar puntos de entrada según la calidad
    if quality_entry_point_1 < quality_threshold:
        logger.info(f"Entry Point 1 no cumple con el umbral de calidad. Se omite.")
        entry_point_1 = None

    if quality_entry_point_2 < quality_threshold:
        logger.info(f"Entry Point 2 no cumple con el umbral de calidad. Se omite.")
        entry_point_2 = None

    # Retornar el mejor punto de entrada basado en la calidad
    if entry_point_1 and entry_point_2:
        return (entry_point_1, entry_point_2) if quality_entry_point_1 >= quality_entry_point_2 else (entry_point_2, entry_point_1)
    elif entry_point_1:
        return entry_point_1, None
    elif entry_point_2:
        return entry_point_2, None
    else:
        logger.info(f"No se encontraron puntos de entrada válidos para {symbol}.")
        return None, None
    


def handle_null_values(data, symbol):
    # Verificar y registrar valores nulos en columnas específicas
    if data.isnull().values.any():
        # Identificar columnas con nulos
        null_columns = data.columns[data.isnull().any()].tolist()
        logger.error(f"Error: Existen valores nulos en los datos de {symbol}. Columnas con nulos: {null_columns}")

        # Llenar nulos hacia adelante y luego eliminar filas que aún tengan nulos
        data = data.fillna(method='ffill').dropna()

        # Verificar si persisten nulos después del tratamiento
        if data.isnull().values.any():
            remaining_nulls = data.columns[data.isnull().any()].tolist()
            logger.error(f"Persisten valores nulos en {symbol} tras el tratamiento. Columnas con nulos: {remaining_nulls}")
            return None  # Omitir este símbolo si los nulos persisten

    # Verificar y eliminar duplicados
    if data.duplicated().any():
        logger.info(f"Datos duplicados encontrados para {symbol}. Eliminando duplicados.")
        data = data.drop_duplicates()
        if data.empty:
            logger.error(f"Error: Después de eliminar duplicados, los datos de {symbol} están vacíos. Saltando análisis.")
            return None
    return data




def check_market_conditions(data):
    # Condiciones mínimas de volatilidad y volumen
    atr = data['atr'].iloc[-1]
    avg_volume = data['volume'].mean()

    # Evitar mercados con baja volatilidad o liquidez
    if atr < data['close'].mean() * 0.005 or avg_volume < 1000:
        logger.info("Condiciones de mercado inadecuadas: baja volatilidad o liquidez")
        return False
    return True



def calculate_stop_loss_take_profit(entry_price, data, trend):
    """
    Calcula el stop loss y los objetivos de ganancias con ATR.
    """
    if 'atr' not in data.columns:
        calculate_atr(data)
    
    atr = data['atr'].iloc[-1]
    rsi = data['rsi'].iloc[-1]
    
    if trend == "up":
        stop_loss = entry_price - atr * 1.5
        take_profits = calculate_take_profits(entry_price, atr, rsi, trend="up")
    else:
        stop_loss = entry_price + atr * 1.5
        take_profits = calculate_take_profits(entry_price, atr, rsi, trend="down")
    
    signal_strength = calculate_signal_strength(data, trend, entry_price)
    return stop_loss, take_profits, signal_strength



def calculate_take_profits(entry_price, atr, rsi, trend):
    if trend == "up":
        if rsi < 20:
            return [
                entry_price + atr * 3,
                entry_price + atr * 5,
                entry_price + atr * 8,
                entry_price + atr * 10
            ]
        else:
            return [
                entry_price + atr * 2,
                entry_price + atr * 3,
                entry_price + atr * 5,
                entry_price + atr * 7
            ]
    else:
        if rsi > 80:
            return [
                entry_price - atr * 3,
                entry_price - atr * 5,
                entry_price - atr * 8,
                entry_price - atr * 10
            ]
        else:
            return [
                entry_price - atr * 2,
                entry_price - atr * 3,
                entry_price - atr * 5,
                entry_price - atr * 7
            ]



def check_fibonacci_level(entry_price, data):
    """
    Verifica si el precio de entrada está cerca de un nivel de Fibonacci.
    """
    fibonacci_levels = [
        data['fibonacci_0.236'],
        data['fibonacci_0.382'],
        data['fibonacci_0.5'],
        data['fibonacci_0.618'],
        data['fibonacci_0.786'],
        data['fibonacci_1.0']
    ]
    
    # Definir un margen de tolerancia para considerar si el precio está cerca del nivel de Fibonacci
    tolerance = 0.01 * data['close'].mean()

    # Verificar si el precio de entrada está cerca de algún nivel de Fibonacci
    for level in fibonacci_levels:
        if abs(entry_price - level) <= tolerance:
            return True

    return False


def check_ichimoku_support(entry_price, data):
    """
    Verifica si el precio de entrada está cerca del soporte o resistencia del Ichimoku.
    """
    senkou_span_a = data['senkou_span_a'].iloc[-1]
    senkou_span_b = data['senkou_span_b'].iloc[-1]

    # Definir un margen de tolerancia para considerar si el precio está cerca del soporte o resistencia
    tolerance = 0.01 * data['close'].mean()

    # Verificar si el precio de entrada está cerca de Senkou Span A o B
    if abs(entry_price - senkou_span_a) <= tolerance or abs(entry_price - senkou_span_b) <= tolerance:
        return True

    return False





def calculate_signal_strength(data, trend, entry_price):
    rsi = data['rsi'].iloc[-1]
    macd = data['macd'].iloc[-1]
    signal_macd = data['macd_signal'].iloc[-1]  # Línea de señal del MACD
    close_price = data['close'].iloc[-1]

    # Normalización de RSI y MACD
    rsi_norm = (rsi - 20) / 60
    macd_range = data['macd'].max() - data['macd'].min()
    macd_norm = (macd - data['macd'].min()) / macd_range if macd_range > 0 else 0.5

    # Ajuste basado en la diferencia del precio de entrada con el cierre actual
    price_diff = abs(close_price - entry_price)
    price_adjustment = max(0, 1 - (price_diff / close_price))  # Ajuste si el precio de entrada está lejos

    # Nuevo ajuste basado en Fibonacci y Ichimoku
    fibonacci_level = check_fibonacci_level(entry_price, data)  # Función que verifica si está en un nivel clave de Fibonacci
    ichimoku_support = check_ichimoku_support(entry_price, data)  # Función que verifica soporte/resistencia de Ichimoku

    if fibonacci_level or ichimoku_support:
        price_adjustment *= 1.2  # Aumentar la fuerza si hay soporte adicional de Fibonacci o Ichimoku

    # Ajuste adicional basado en RSI extremo
    if trend == "up" and rsi < 30 and entry_price < close_price:
        price_adjustment *= 1.2  # Aumentar si el RSI indica sobreventa y el punto de entrada está más abajo
    elif trend == "down" and rsi > 70 and entry_price > close_price:
        price_adjustment *= 1.2  # Aumentar si el RSI indica sobrecompra y el punto de entrada está más arriba

    # Ajuste basado en el MACD:
    if trend == "up" and macd > signal_macd and macd > 0:
        price_adjustment *= 1.2  # Aumentar si el MACD está en un cruce alcista
    elif trend == "down" and macd < signal_macd and macd < 0:
        price_adjustment *= 1.2  # Aumentar si el MACD está en un cruce bajista

    # Cálculo final de la fuerza de la señal
    if trend == "up":
        strength = (rsi_norm + macd_norm) / 2 * price_adjustment
    else:
        strength = ((1 - rsi_norm) + (1 - macd_norm)) / 2 * price_adjustment

    return strength * 100


def adjust_entry_point(entry_price, data, trend):
    """
    Ajusta el punto de entrada basado en el ATR (rango verdadero promedio) y la tendencia.
    """
    atr = data['atr'].iloc[-1]  # Calcula el ATR a partir de los datos de precios
    price_to_vwap = abs(entry_price - data['vwap'].iloc[-1]) / data['vwap'].iloc[-1]

    if trend == "up":
        # Si la tendencia es alcista, ajusta ligeramente al alza si el precio está cerca del VWAP
        adjusted_entry = entry_price + atr * 0.1 if price_to_vwap < 0.02 else entry_price
    elif trend == "down":
        # Si la tendencia es bajista, ajusta ligeramente a la baja si el precio está cerca del VWAP
        adjusted_entry = entry_price - atr * 0.1 if price_to_vwap < 0.02 else entry_price
    else:
        # No hay ajuste si no se detecta una tendencia
        adjusted_entry = entry_price

    return adjusted_entry


def process_entry(entry, data, trend):
    if entry:
        entry = adjust_entry_point(entry, data, trend)
        entry_2 = adjust_secondary_entry(entry, data, trend)
        stop_loss, take_profits, signal_strength = calculate_stop_loss_take_profit(entry, data, trend)
        if validate_entry(entry, stop_loss, take_profits):
            return entry, entry_2, stop_loss, take_profits, signal_strength
    return None, None, None, None, None

def validate_entry(entry, stop_loss, take_profits):
    threshold = 0.01  # Umbral de proximidad
    for level in [stop_loss] + take_profits:
        if abs(entry - level) < threshold:
            return False
    return True

def adjust_secondary_entry(entry, data, trend):
    atr = data['atr'].iloc[-1]
    if trend == "up":
        return entry - atr * 0.5
    else:
        return entry + atr * 0.5

def prepare_return(entry, entry_2, stop_loss, take_profits, signal_strength, signal_type):
    if entry and stop_loss and take_profits:
        return (entry, entry_2, stop_loss, *take_profits, signal_type, signal_strength)
    return None

def calculate_volume_profile(data):
    volume_profile = {}
    for i, row in data.iterrows():
        price = row['close']
        volume = row['volume']
        if price in volume_profile:
            volume_profile[price] += volume
        else:
            volume_profile[price] = volume
    return volume_profile

def filter_signal(result, symbol):
    if result is None:
        return None

    entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength = result

    unique_values = {entry1, entry2, stop_loss, tp1, tp2, tp3, tp4}
    if None in unique_values or len(unique_values) != 7:
        logger.info(f"Señal para {symbol} ({signal_type}) filtrada por valores repetidos o nulos.")
        return None

    if signal_strength < 70:
        logger.info(f"Señal para {symbol} ({signal_type}) filtrada por fuerza insuficiente.")
        return None

    risk = abs(entry1 - stop_loss)
    reward = abs(tp2 - entry1)
    rr_ratio = reward / risk if risk > 0 else 0

    if rr_ratio < 2:
        logger.info(f"Señal para {symbol} filtrada por ratio riesgo/recompensa insuficiente: {rr_ratio:.2f}")
        return None

    return result





SIGNAL_FILE = os.path.join(os.path.dirname(__file__), 'signals.json')

def send_signal(symbol, result, sentiment):
    try:
        entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength = result

        if None in [entry1, entry2, stop_loss, tp1, tp2, tp3, tp4]:
            logger.error(f"Valores nulos en la señal para {symbol}.")
            return

        message = (
            f"🚀 {symbol} - #{signal_type} - FUTURES\n"
            f"📍 Entry Point 1: {entry1:.4f}\n"
            f"📍 Entry Point 2: {entry2:.4f}\n"
            f"🛑 Stop Loss: {stop_loss:.4f}\n"
            f"🎯 Take Profit 1: {tp1:.4f}\n"
            f"🎯 Take Profit 2: {tp2:.4f}\n"
            f"🎯 Take Profit 3: {tp3:.4f}\n"
            f"🎯 Take Profit 4: {tp4:.4f}\n"
            f"💪 Signal Strength: {signal_strength:.2f}%\n"
            f"📊 Market Sentiment: {sentiment}\n"
        )

        # Simulación del envío al dashboard
        response = send_to_dashboard(message)
        if response.status_code == 200:
            logger.info(f"Señal para {symbol} enviada correctamente al dashboard")
        else:
            logger.error(f"Error al enviar la señal de {symbol} al dashboard: {response.text}")

    except Exception as e:
        logger.error(f"Error al enviar la señal: {e}")

def send_to_dashboard(message):
    class Response:
        def __init__(self, status_code, text="Success"):
            self.status_code = status_code
            self.text = text

    # Simulación de envío
    return Response(200)


def send_to_dashboard(message):
    """
    Simula el envío de una señal al dashboard o sistema de notificaciones.
    Aquí puedes implementar la lógica real para enviar la señal.
    """
    # Simulación de respuesta correcta
    class Response:
        def __init__(self, status_code, text="Success"):
            self.status_code = status_code
            self.text = text

    # Supón que el envío fue exitoso
    return Response(200)


def analyze_with_ichimoku_theories(data, symbol, last_signal={}):
    """
    Integra la teoría del tiempo, ondas y precios para generar señales de trading.
    """
    try:
        # Calcula el Ichimoku
        data = calculate_ichimoku(data)
        
        # Detecta ciclos de tiempo a partir de cruces
        time_cycles = calculate_time_cycles(data, anchor_point=len(data) - 26)
        
        # Detecta patrones de ondas
        wave_patterns = detect_wave_patterns(data)
        
        # Calcula objetivos de precios
        v_target, e_target, nt_target = calculate_price_targets(data, wave_type='N')
        
        # Determina la señal Ichimoku
        if data['tenkan_sen'].iloc[-1] > data['kijun_sen'].iloc[-1] and data['close'].iloc[-1] > data['senkou_span_a'].iloc[-1]:
            signal = "Buy"
        elif data['tenkan_sen'].iloc[-1] < data['kijun_sen'].iloc[-1] and data['close'].iloc[-1] < data['senkou_span_b'].iloc[-1]:
            signal = "Sell"
        else:
            signal = "Neutral"

        # Log solo si la señal ha cambiado
        if last_signal.get(symbol) != signal:
            logger.info(f"Ichimoku Signal para {symbol}: {signal}")
            last_signal[symbol] = signal

    except Exception as e:
        logger.error(f"Error en el análisis Ichimoku para {symbol}: {e}")
        signal = None
        v_target, e_target, nt_target, time_cycles, wave_patterns = None, None, None, None, None

    # Retorna siempre un diccionario con las claves, aunque alguna falle
    return {
        'signal': signal,
        'price_targets': {'V': v_target, 'E': e_target, 'NT': nt_target} if v_target else None,
        'time_cycles': time_cycles,
        'wave_patterns': wave_patterns
    }





def analyze_ichimoku(data):
    """
    Esta función analiza la señal Ichimoku.
    Calcula las líneas del Ichimoku y retorna una señal de 'Buy', 'Sell' o 'Neutral'.
    """
    try:
        # Calcular Ichimoku
        ichimoku = ta.trend.IchimokuIndicator(high=data['high'], low=data['low'], window1=9, window2=26, window3=52)
        data['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
        data['kijun_sen'] = ichimoku.ichimoku_base_line()
        data['senkou_span_a'] = ichimoku.ichimoku_a()
        data['senkou_span_b'] = ichimoku.ichimoku_b()
        data['chikou_span'] = data['close'].shift(-26)  # Línea Chikou Span

        # Detectar cruces de Tenkan-sen y Kijun-sen
        if data['tenkan_sen'].iloc[-1] > data['kijun_sen'].iloc[-1] and data['close'].iloc[-1] > data['senkou_span_a'].iloc[-1]:
            return 'Buy'  # Señal de compra
        elif data['tenkan_sen'].iloc[-1] < data['kijun_sen'].iloc[-1] and data['close'].iloc[-1] < data['senkou_span_b'].iloc[-1]:
            return 'Sell'  # Señal de venta
        else:
            return 'Neutral'  # Sin señal clara

    except Exception as e:
        logger.error(f"Error en el análisis Ichimoku: {e}")
        return 'Neutral'




def analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
    """
    Realiza el análisis de trading para un símbolo dado si los datos son válidos y completos.
    """
    # Validación inicial de los datos de entrada
    if data is None or data.empty:
        logger.error(f"Error: Datos insuficientes o no válidos para {symbol}. Omitiendo análisis.")
        return False

    # Validación de los datos de BTC (1h y 1d)
    if btc_data_1h is None or btc_data_1h.empty or btc_data_1d is None or btc_data_1d.empty:
        logger.error("Error: Los datos de BTC (1h y 1d) son insuficientes o no válidos. Omitiendo análisis.")
        return False

    # Realizar el análisis de Ichimoku si es necesario
    ichimoku_analysis = analyze_with_ichimoku_theories(data, symbol)
    if ichimoku_analysis is None:
        logger.error(f"Error en el análisis Ichimoku para {symbol}")
        return False

    # Extraer resultados del análisis Ichimoku
    ichimoku_signal = ichimoku_analysis.get('signal')
    price_targets = ichimoku_analysis.get('price_targets')

    logger.info(f"Ichimoku Signal: {ichimoku_signal}")
    logger.info(f"Price Targets: {price_targets}")

    # Calcular perfil de volumen
    hvn_price, lvn_price, volume_profile = calculate_volume_profile_with_nodes(data)
    if volume_profile is None or volume_profile.empty:
        logger.error(f"Error: El perfil de volumen está vacío para {symbol}")
        return False

    # Log de resultados para HVN y LVN
    if hvn_price is not None and lvn_price is not None:
        logger.info(f"Perfil de Volumen calculado para {symbol}. HVN: {hvn_price}, LVN: {lvn_price}")
    else:
        logger.warning(f"No se pudo calcular HVN o LVN para {symbol} debido a valores faltantes o no numéricos.")

    # Evaluar la calidad de la entrada usando la nueva estrategia de `dr`
    quality, decision_color = evaluate_entry_quality(data)

    # Filtrar y decidir si enviar la señal
    if quality >= 7.5:
        selected_result = (ichimoku_signal, price_targets, decision_color, "buy")
    elif quality >= 5.0:
        selected_result = (ichimoku_signal, price_targets, decision_color, "sell")
    else:
        logger.info(f"Condiciones neutrales para {symbol}, omitiendo señal.")
        return False

    # Obtener el sentimiento del mercado
    sentiment, sentiment_score = get_market_sentiment()
    if sentiment:
        logger.info(f"Sentimiento del mercado: {sentiment}, Puntuación: {sentiment_score}")

    # Enviar señal al dashboard
    send_signal(symbol, selected_result, sentiment)
    return True




def get_btc_data(interval, client):
    logger.info(f"Obteniendo datos de BTC ({interval})")
    btc_candles = client.futures_klines(symbol='BTCUSDT', interval=interval, limit=KLINE_LIMIT)
    btc_data = pd.DataFrame(btc_candles,
                            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                     'quote_asset_volume', 'number_of_trades',
                                     'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                     'ignore'])
    for col in ['close', 'high', 'low', 'volume']:
        btc_data[col] = btc_data[col].astype(float)
    return calculate_btc_indicators(btc_data)



def get_symbol_data(symbol, client, retries=2, delay=5):
    """
    Obtiene datos de velas para un símbolo dado y los convierte a DataFrame,
    con un número reducido de reintentos para evitar duplicados de log.
    """
    log_single_instance(symbol, f"Obteniendo datos para {symbol}")
    for attempt in range(retries):
        try:
            candles = client.futures_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
            
            # Confirmación de datos suficientes
            if not candles or len(candles) < KLINE_LIMIT:
                time.sleep(delay)
                continue
            
            data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                                  'close_time', 'quote_asset_volume', 'number_of_trades',
                                                  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            for col in ['close', 'high', 'low', 'volume']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
                
            data = data.dropna().drop_duplicates()  # Eliminar nulos y duplicados

            if data.empty:
                log_single_instance(symbol, f"Error: Datos insuficientes para {symbol}, omitiendo análisis.")
            else:
                return data

        except Exception as e:
            log_single_instance(symbol, f"Error al obtener datos para {symbol}: {e}")
            time.sleep(delay)

    log_single_instance(symbol, f"Error: No se pudieron obtener datos válidos para {symbol} después de {retries} intentos.")
    return None





def select_random_symbols(client):
    exchange_info = client.futures_exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')]
    random.shuffle(symbols)
    return symbols[:5]




def handle_null_values(data, symbol):
    # Verificar y eliminar valores nulos
    if data.isnull().values.any():
        logger.error(f"Error: Existen valores nulos en los datos de {symbol}. Eliminando nulos.")
        data = data.dropna()  # Eliminar filas con valores nulos
        if data.empty:
            logger.error(f"Error: Después de eliminar los nulos, los datos de {symbol} están vacíos. Saltando análisis.")
            return None
    
    # Verificar y eliminar duplicados
    if data.duplicated().any():
        logger.info(f"Datos duplicados encontrados para {symbol}. Eliminando duplicados.")
        data = data.drop_duplicates()  # Eliminar duplicados
        if data.empty:
            logger.error(f"Error: Después de eliminar duplicados, los datos de {symbol} están vacíos. Saltando análisis.")
            return None
    return data



# Define la función `clear_cache` para limpiar el caché global
def clear_cache():
    """
    Limpia el caché global de `volume_profile_cache` para evitar mensajes duplicados.
    """
    volume_profile_cache.clear()

# Función principal de análisis con control de duplicados
def perform_trade_analysis():
    """
    Función principal para el análisis de trading.
    Realiza iteraciones de análisis de mercado, calcula perfiles de volumen,
    y limpia el caché al finalizar cada ciclo.
    """
    logger.info("Iniciando análisis de trading avanzado")
    
    while True:
        # Limpiar el caché al inicio de cada iteración
        clear_cache()
        
        # Seleccionar aleatoriamente un conjunto de símbolos
        symbols = select_random_symbols(client)

        for symbol in symbols:
            try:
                # Obtener datos de trading del símbolo
                data = get_symbol_data(symbol, client)
                if data is None or data.empty:
                    log_single_instance(symbol, f"Error: Datos insuficientes para {symbol}, omitiendo análisis.")
                    continue

                # Calcular perfil de volumen
                try:
                    hvn_price, lvn_price, volume_profile = calculate_volume_profile_with_nodes(data)
                    if volume_profile is not None and isinstance(volume_profile, pd.DataFrame) and not volume_profile.empty:
                        log_volume_profile(symbol, hvn_price, lvn_price)
                    else:
                        log_single_instance(symbol, f"Perfil de volumen vacío o no válido para {symbol}.")
                except ValueError as e:
                    log_single_instance(symbol, f"Error al calcular perfil de volumen para {symbol}: {e}")

                # Registrar condiciones neutrales si es necesario
                log_neutral_condition(symbol)

            except Exception as e:
                log_single_instance(symbol, f"Error al analizar {symbol}: {e}")
                continue

        logger.info("Ciclo completo, esperando antes de la siguiente iteración")
        time.sleep(120)  # Tiempo de espera antes de la siguiente iteración


# Función para obtener datos del símbolo con control de intentos y log optimizado
def get_symbol_data(symbol, client, retries=2, delay=5):
    """
    Obtiene datos de velas para un símbolo dado y los convierte a DataFrame,
    con un número reducido de reintentos para evitar duplicados de log.
    """
    log_single_instance(symbol, f"Obteniendo datos para {symbol}")
    for attempt in range(retries):
        try:
            candles = client.futures_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
            
            # Confirmación de datos suficientes
            if not candles or len(candles) < KLINE_LIMIT:
                time.sleep(delay)
                continue
            
            data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                                  'close_time', 'quote_asset_volume', 'number_of_trades',
                                                  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            for col in ['close', 'high', 'low', 'volume']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
                
            data = data.dropna().drop_duplicates()  # Eliminar nulos y duplicados

            if data.empty:
                log_single_instance(symbol, f"Error: Datos insuficientes para {symbol}, omitiendo análisis.")
            else:
                return data

        except Exception as e:
            log_single_instance(symbol, f"Error al obtener datos para {symbol}: {e}")
            time.sleep(delay)

    log_single_instance(symbol, f"Error: No se pudieron obtener datos válidos para {symbol} después de {retries} intentos.")
    return None


            

# -----------------------------------
# Almacenamos las senales 
# -----------------------------------


SIGNAL_FILE = os.path.join(os.path.dirname(__file__), 'signals.json')

def store_signal(signal_data):
    """
    Almacena la señal en un archivo JSON.
    Si no hay señal, asegura que el archivo siempre exista.
    """
    try:
        # Si no hay señal, guarda un estado por defecto
        if not signal_data:
            signal_data = {'signal': None, 'message': 'No signal available yet'}

        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal_data, f)
        logger.info("Señal almacenada correctamente.")
    except Exception as e:
        logger.error(f"Error al almacenar la señal: {e}")

def load_signal():
    """
    Carga la señal almacenada desde el archivo JSON.
    """
    if not os.path.exists(SIGNAL_FILE):
        # Si el archivo no existe, devolver una señal por defecto
        return {'signal': None, 'message': 'No signal file found'}
    
    try:
        with open(SIGNAL_FILE, 'r') as f:
            signal_data = json.load(f)
        return signal_data
    except Exception as e:
        logger.error(f"Error al cargar la señal: {e}")
        return {'signal': None, 'message': 'Error loading signal file'}


def send_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross=None, sentiment=None):
    """
    En lugar de enviar la señal directamente, almacenaremos los resultados.
    """
    signal_data = {
        'symbol': symbol,
        'entry1': entry1,
        'entry2': entry2,
        'stop_loss': stop_loss,
        'take_profits': [tp1, tp2, tp3, tp4],
        'signal_type': signal_type,
        'signal_strength': signal_strength,
        'ema_cross': ema_cross,
        'sentiment': sentiment
    }
    store_signal(signal_data)  # Guardar la señal



if __name__ == "__main__":
    thread = threading.Thread(target=perform_trade_analysis)
    thread.start()