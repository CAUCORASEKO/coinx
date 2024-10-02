# trade_signal.py
import sys
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

# Asegúrate de que la ruta de importación esté correcta para obtener el cliente
from web.management.commands.global_client import get_global_client  # Importa el cliente global

# Establecer la variable DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
# Ajusta con tu proyecto

# Inicializa Django
django.setup()

# Configuración del logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Obtener el cliente de Binance
client = get_global_client()

if client is None:
    logger.error("No se pudo inicializar el cliente global de Binance. Abortando.")
    sys.exit(1)


# Configuración centralizada
KLINE_INTERVAL = '1h'
KLINE_LIMIT = 100
ORDER_BOOK_LIMIT = 100

# Configuración del logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Obtener el cliente de Binance desde global_client.py


if client is None:
    logger.error("No se pudo inicializar el cliente global de Binance. Abortando.")
    sys.exit(1)  # Termina el script si no hay cliente


# Función para obtener información de la cuenta
def fetch_futures_account(client, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = client.futures_account()
            logger.info(f"Datos de la cuenta: {response}")
            if isinstance(response, dict):
                return response
        except (BinanceAPIException, Exception) as e:
            logger.error(f"Error durante la solicitud API: {e}")
            time.sleep(delay)
    logger.error("Se excedió el máximo de reintentos para la API de Binance.")
    return None


# Llama a la función para obtener el resultado de la cuenta de futuros
account_data = fetch_futures_account(client)

if account_data is None:
    logger.error("No se pudo obtener la cuenta de futuros. Abortando.")
else:
    logger.info(f"Datos de cuenta: {account_data}")


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
    return levels



def get_market_cap_from_coingecko(crypto_id):
    """
    Obtiene el Market Cap desde CoinGecko para una criptomoneda especificada.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            market_cap = data['market_data']['market_cap']['usd']
            return market_cap
        else:
            logger.error(f"Error al obtener Market Cap para {crypto_id} de CoinGecko. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener Market Cap de CoinGecko: {e}")
        return None
    
    
    



def analyze_btc_market_cap(btc_data):
    """
    Realiza el análisis de BTC y añade el Market Cap y otros indicadores técnicos al resultado.
    """
    # Obtener el Market Cap de BTC desde CoinGecko
    btc_market_cap = get_market_cap_from_coingecko('bitcoin')

    if btc_market_cap:
        logger.info(f"Market Cap de BTC: ${btc_market_cap:,.2f}")

    # Realizar el análisis de BTC (indicadores técnicos)
    
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
    btc_data = calculate_ichimoku(btc_data)  # Función ya implementada en tu script

    # 8. Perfilador de Volumen
    volume_profile = calculate_volume_profile_with_nodes(btc_data)
    logger.info(f"Perfil de Volumen: {volume_profile}")

    # 9. Fibonacci (Retrocesos y Extensiones)
    high = btc_data['high'].max()  # Obtener el valor máximo
    low = btc_data['low'].min()    # Obtener el valor mínimo
    fibonacci_levels = calculate_fibonacci_levels(high, low)  # Asegurarse de pasar ambos valores
    logger.info(f"Niveles de Fibonacci calculados: {fibonacci_levels}")

    return btc_data




def analyze_random_symbol_market_cap(symbol, data):
    """
    Realiza el análisis para un símbolo aleatorio, incluyendo el cálculo del Market Cap.
    """
    # Obtener la criptomoneda base del símbolo (por ejemplo, "BTC" en "BTCUSDT")
    crypto_base = symbol.replace("USDT", "").lower()

    # Obtener el Market Cap de la criptomoneda base
    market_cap = get_market_cap_from_coingecko(crypto_base)
    
    if market_cap:
        logger.info(f"Market Cap de {crypto_base.upper()}: ${market_cap:,.2f}")
    else:
        logger.error(f"No se pudo obtener el Market Cap para {crypto_base.upper()}.")

    # Realizar el análisis de indicadores técnicos para el símbolo
    data = calculate_technical_indicators(data)
    
    return data
   
    
    

def get_order_book(symbol):
    for _ in range(3):
        try:
            order_book = client.futures_order_book(symbol=symbol, limit=ORDER_BOOK_LIMIT)
            bids = [(float(bid[0]), float(bid[1])) for bid in order_book['bids']]
            asks = [(float(ask[0]), float(ask[1])) for ask in order_book['asks']]
            if bids and asks:
                return bids, asks
        except Exception as e:
            logger.error(f"Error al obtener el libro de órdenes para {symbol}: {e}")
        time.sleep(2)
    return [], []


def calculate_weighted_average_price(levels):
    total_volume = sum(size for price, size in levels)
    if total_volume == 0:
        logger.error("El volumen total es 0, no se puede calcular el precio ponderado.")
        return None
    weighted_avg_price = sum(price * size for price, size in levels) / total_volume
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

def calculate_emas(data, short_period=9, long_period=26):
    """
    Calcula las EMAs (medias móviles exponenciales) para los períodos corto y largo.
    """
    data['ema_short'] = ta.trend.ema_indicator(data['close'], window=short_period)
    data['ema_long'] = ta.trend.ema_indicator(data['close'], window=long_period)
    return data

def detect_ema_cross(data):
    """
    Detecta un cruce de EMAs en los datos.
    """
    if data['ema_short'].iloc[-2] < data['ema_long'].iloc[-2] and data['ema_short'].iloc[-1] > data['ema_long'].iloc[-1]:
        return "Bullish Cross"
    elif data['ema_short'].iloc[-2] > data['ema_long'].iloc[-2] and data['ema_short'].iloc[-1] < data['ema_long'].iloc[-1]:
        return "Bearish Cross"
    return None

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
    
    if last_volume > mid_term_avg_volume * volume_threshold and last_volume > short_term_avg_volume * 1.2:
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

    Parámetros:
    - price: Precio actual.
    - support: Nivel de soporte identificado.
    - resistance: Nivel de resistencia identificado.
    - bids: Lista de órdenes de compra [(precio, volumen)].
    - asks: Lista de órdenes de venta [(precio, volumen)].
    - spread_threshold: Umbral del spread entre bids y asks.
    - data: DataFrame con datos históricos del precio (puede incluir velas, ATR, etc.).
    - interval: Intervalo de las velas (por defecto usa KLINE_INTERVAL).
    - limit: Límite de cantidad de velas a analizar (por defecto usa KLINE_LIMIT).
    
    Devuelve:
    - True si se detecta una posible caza de stop losses.
    """
    try:
        # Calcular el spread entre las órdenes de compra y venta
        spread = asks[0][0] - bids[0][0]
        
        # Calcular ATR a partir de los datos históricos si están disponibles
        if data is not None:
            # Si el DataFrame tiene menos de limit velas, ajusta dinámicamente
            actual_limit = min(len(data), limit)
            atr = ta.volatility.average_true_range(
                data['high'].iloc[-actual_limit:], 
                data['low'].iloc[-actual_limit:], 
                data['close'].iloc[-actual_limit:]
            ).iloc[-1]
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

    # Verificar si los precios ponderados son None
    if weighted_buy_price is None or weighted_sell_price is None:
        logger.error(f"No se pudieron obtener precios ponderados para {symbol}, omitiendo análisis.")
        return None, None

    # Calcular indicadores técnicos
    data = calculate_technical_indicators(data)
    if data is None or 'ema_50' not in data.columns or 'ema_200' not in data.columns:
        logger.error(f"Error: No se pudieron calcular las EMAs para {symbol}")
        return None, None


    # Calcular la fuerza combinada usando la nueva función
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
        data['vwap'] = calculate_vwap(data)
        data['atr'] = ta.volatility.average_true_range(data['high'], data['low'], data['close'])
        data['ema_50'] = ta.trend.ema_indicator(data['close'], window=50)
        data['ema_200'] = ta.trend.ema_indicator(data['close'], window=200)
        data['rsi'] = ta.momentum.rsi(data['close'])
        data['mfi'] = ta.volume.money_flow_index(data['high'], data['low'], data['close'], data['volume'])
        data['macd'] = ta.trend.macd_diff(data['close'])
        calculate_ichimoku(data)
    except Exception as e:
        logger.error(f"Error al calcular los indicadores técnicos: {e}")
        return None
    return data


def evaluate_entry_quality(trend, price, vwap, atr, rsi, macd, ema_50, tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, volume_profile):
    """
    Evalúa la calidad de un punto de entrada basado en indicadores técnicos y perfiles de volumen.
    Devuelve un puntaje de calidad mayor si las condiciones del mercado son favorables.
    """
    price_to_vwap = abs(price - vwap) / vwap
    atr_factor = abs(price - vwap) / atr

    # Asegurarse de que el precio tiene un volumen asociado en el perfil
    volume_at_price = volume_profile.get(price, 0)

    # Ajustar el peso del perfil de volumen según HVN/LVN
    is_hvn = volume_profile['HVN'].iloc[-1] if 'HVN' in volume_profile else False
    is_lvn = volume_profile['LVN'].iloc[-1] if 'LVN' in volume_profile else False
    volume_score = 1.5 if is_lvn else 0.5 if is_hvn else 1.0  # LVN favorece entradas más agresivas

    # Cálculo de la calidad basado en la tendencia del mercado y otros indicadores
    if trend == "up":
        quality = (
            (price > tenkan_sen) * 0.7 +   # Precio mayor a la Tenkan-sen
            (price > kijun_sen) * 0.7 +    # Precio mayor a la Kijun-sen
            (price > ema_50) * 0.7 +       # Precio mayor a la EMA 50
            (1 if 20 < rsi < 80 else 0) * 1.2 +  # RSI en rango saludable
            (1 if macd > 0 else 0) * 1.0 +       # MACD indicando tendencia positiva
            (1 - min(price_to_vwap, 1)) * 1.0 +  # Proximidad al VWAP, más cerca es mejor
            (price > senkou_span_a) * 0.7 +      # Precio mayor a la Senkou Span A
            (price > senkou_span_b) * 0.7 +      # Precio mayor a la Senkou Span B
            (1 if atr_factor < 1.0 else 0) * 1.0 + # Bajo factor ATR
            volume_score                        # Puntaje de volumen basado en HVN/LVN
        )
    else:
        quality = (
            (price < tenkan_sen) * 0.7 +   # Precio menor a la Tenkan-sen
            (price < kijun_sen) * 0.7 +    # Precio menor a la Kijun-sen
            (price < ema_50) * 0.7 +       # Precio menor a la EMA 50
            (1 if 20 < rsi < 80 else 0) * 1.2 +  # RSI en rango saludable
            (1 if macd < 0 else 0) * 1.0 +       # MACD indicando tendencia negativa
            (1 - min(price_to_vwap, 1)) * 1.0 +  # Proximidad al VWAP, más cerca es mejor
            (price < senkou_span_a) * 0.7 +      # Precio menor a la Senkou Span A
            (price < senkou_span_b) * 0.7 +      # Precio menor a la Senkou Span B
            (1 if atr_factor < 1.0 else 0) * 1.0 + # Bajo factor ATR
            volume_score                        # Puntaje de volumen basado en HVN/LVN
        )
    
    return quality



def calculate_volume_profile_with_nodes(data, num_bins=20, volume_threshold=0.05):
    """
    Calcula el perfil de volumen y detecta nodos de alto y bajo volumen (HVN/LVN).

    :param data: DataFrame con las columnas 'close' (precio de cierre), 'volume' (volumen) y 'atr' (volatilidad).
    :param num_bins: Número de bins para dividir los precios.
    :param volume_threshold: Umbral para definir HVN/LVN como porcentaje del volumen total.
    :return: DataFrame con el rango de precios, volumen, HVN y LVN.
    """
    # Verificar que los datos tengan las columnas necesarias
    if 'close' not in data.columns or 'volume' not in data.columns or 'atr' not in data.columns:
        raise ValueError("El DataFrame de entrada debe contener las columnas 'close', 'volume' y 'atr'.")

    # Definir los límites de los bins de precios
    price_min = data['close'].min()
    price_max = data['close'].max()
    bins = np.linspace(price_min, price_max, num_bins)
    
    # Agrupar los precios en bins y sumar el volumen por cada rango de precios
    data['price_bin'] = pd.cut(data['close'], bins=bins, include_lowest=True)
    volume_profile = data.groupby('price_bin', observed=False)['volume'].sum().reset_index()

    # Calcular el volumen total
    total_volume = volume_profile['volume'].sum()

    # Ajustar dinámicamente el umbral de volumen en función de la volatilidad (ATR)
    volume_threshold_adjusted = volume_threshold * (1 + data['atr'].iloc[-1] / data['close'].mean())

    # Asegurarse de que el volumen total no sea 0 para evitar divisiones por 0
    if total_volume == 0:
        raise ValueError("El volumen total es cero, no se puede calcular el perfil de volumen.")

    # Calcular el porcentaje de volumen para cada bin
    volume_profile['volume_percent'] = volume_profile['volume'] / total_volume

    # Detectar nodos de alto volumen (HVN) y nodos de bajo volumen (LVN)
    volume_profile['HVN'] = volume_profile['volume_percent'] > volume_threshold_adjusted
    volume_profile['LVN'] = volume_profile['volume_percent'] < (volume_threshold_adjusted / 2)

    # Limpiar la columna auxiliar 'price_bin' si ya no es necesaria
    data.drop(columns=['price_bin'], inplace=True, errors='ignore')

    return volume_profile






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
    atr = data['atr'].iloc[-1]
    rsi = data['rsi'].iloc[-1]
    
    # Ajustar el multiplicador ATR en función de la volatilidad actual
    atr_multiplier = 2 if atr > data['close'].mean() * 0.01 else 1.5

    if trend == "up":
        stop_loss = entry_price - atr * atr_multiplier
        take_profits = calculate_take_profits(entry_price, atr, rsi, trend="up")
    else:
        stop_loss = entry_price + atr * atr_multiplier
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



def calculate_signal_strength(data, trend, entry_price):
    rsi = data['rsi'].iloc[-1]
    macd = data['macd'].iloc[-1]

    rsi_norm = (rsi - 20) / 60
    macd_range = data['macd'].max() - data['macd'].min()
    macd_norm = (macd - data['macd'].min()) / macd_range if macd_range > 0 else 0.5

    if trend == "up":
        strength = (rsi_norm + macd_norm) / 2
    else:
        strength = ((1 - rsi_norm) + (1 - macd_norm)) / 2

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
    entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength = result

    unique_values = {entry1, entry2, stop_loss, tp1, tp2, tp3, tp4}
    if len(unique_values) != 7:
        logger.info(f"Señal para {symbol} ({signal_type}) filtrada por valores repetidos.")
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

def send_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross=None, sentiment=None):
    """
    Envía una señal de trading con la información sobre los puntos de entrada, stop loss, take profits,
    cruces de EMAs y sentimiento de mercado.
    """
    try:
        # Verificar si hay valores nulos
        unique_values = {entry1, entry2, stop_loss, tp1, tp2, tp3, tp4}
        if None in unique_values or len(unique_values) != 7:
            logger.error(f"Error en señal: No deben haber valores nulos en Entry Points, Stop Loss y Take Profits.")
            return

        # Ordenar entry points de acuerdo al tipo de señal
        if signal_type == "Long":
            entry1, entry2 = sorted([entry1, entry2], reverse=True)
        else:
            entry1, entry2 = sorted([entry1, entry2])

        # Cálculo de porcentajes para los take profits y stop loss
        tp1_percent = (tp1 - entry1) / entry1 * 100 * (1 if signal_type == "Long" else -1)
        tp2_percent = (tp2 - entry1) / entry1 * 100 * (1 if signal_type == "Long" else -1)
        tp3_percent = (tp3 - entry1) / entry1 * 100 * (1 if signal_type == "Long" else -1)
        tp4_percent = (tp4 - entry1) / entry1 * 100 * (1 if signal_type == "Long" else -1)
        sl_percent = (stop_loss - entry1) / entry1 * 100 * (1 if signal_type == "Long" else -1)

        # Mensajes adicionales para sentimiento y cruce de EMAs
        sentiment_message = ""
        if sentiment:
            if (signal_type == "Long" and sentiment == "Bearish") or (signal_type == "Short" and sentiment == "Bullish"):
                sentiment_message = "⚠️ Sentiment: Risky"

        ema_cross_message = f"🔀 EMAs Crossing: {ema_cross}" if ema_cross else ""

        # Crear el mensaje a enviar
        message = (
            f"🚀 {symbol} - #{signal_type} - FUTURES\n"
            "--------------------------------------\n"
            f"📍 Entry Point 1   : {entry1:.4f}\n"
            f"📍 Entry Point 2   : {entry2:.4f}\n"
            f"🛑 Stop Loss     : {stop_loss:.4f} ({sl_percent:.2f}%)\n\n"
            f"🎯 Take Profit 1 : {tp1:.4f} ({tp1_percent:.2f}%)\n"
            f"🎯 Take Profit 2 : {tp2:.4f} ({tp2_percent:.2f}%)\n"
            f"🎯 Take Profit 3 : {tp3:.4f} ({tp3_percent:.2f}%)\n"
            f"🎯 Take Profit 4 : {tp4:.4f} ({tp4_percent:.2f}%)\n\n"
            f"💪 Signal Strength: {signal_strength:.2f}%\n"
            f"📊 Signal Quality: {'🔥 Good' if signal_strength > 75 else '✅ Normal'}\n"
            f"{sentiment_message}\n"
            f"{ema_cross_message}\n"
        )

        # Envío de mensaje al dashboard a través de una API, archivo o servicio
        # Aquí debes implementar el código para enviar la señal, dependiendo de cómo esté configurada tu aplicación.
        # Por ejemplo, podrías enviar la señal a un servicio de notificaciones o a un dashboard:

        # Ejemplo de envío (debes adaptar esto a tu lógica real de envío):
        response = send_to_dashboard(message)  # Implementar esta función según tu lógica de envío

        if response.status_code == 200:
            logger.info(f"Señal para {symbol} enviada correctamente a dashboard")
        else:
            logger.error(f"Error al enviar señal de {symbol} a dashboard: {response.text}")

    except Exception as e:
        logger.error(f"Error al enviar señal de {symbol} a dashboard: {str(e)}")


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


def analyze_with_ichimoku_theories(data, symbol):
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
        
        # Usa todo esto para emitir señales
        signal = None
        if data['ichimoku_cross'].iloc[-1] == 'Bullish Cross' and data['close'].iloc[-1] > data['senkou_span_a'].iloc[-1]:
            signal = "Buy"
        elif data['ichimoku_cross'].iloc[-1] == 'Bearish Cross' and data['close'].iloc[-1] < data['senkou_span_b'].iloc[-1]:
            signal = "Sell"
    
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



def analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
    data = calculate_emas(data)
    ema_cross = detect_ema_cross(data)

    # Análisis Ichimoku
    ichimoku_analysis = analyze_with_ichimoku_theories(data, symbol)

    # Acceder a los resultados de Ichimoku
    ichimoku_signal = ichimoku_analysis.get('signal')
    price_targets = ichimoku_analysis.get('price_targets')
    time_cycles = ichimoku_analysis.get('time_cycles')
    wave_patterns = ichimoku_analysis.get('wave_patterns')

    # Registrar información de Ichimoku
    if ichimoku_signal:
        logger.info(f"Señal Ichimoku detectada: {ichimoku_signal}")
    if price_targets:
        logger.info(f"Objetivos de precio calculados: V={price_targets['V']}, E={price_targets['E']}, NT={price_targets['NT']}")
    if time_cycles:
        logger.info(f"Ciclos de tiempo detectados: {time_cycles}")
    if wave_patterns:
        logger.info(f"Patrones de ondas detectados: {wave_patterns}")

    # Procesar señales de EMAs
    if ema_cross:
        if ema_cross == "Bullish Cross":
            logger.info(f"Cruce de EMAs detectado: {ema_cross}. Preparando señal LONG para {symbol}.")
            result_long, result_short = calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d)
            selected_result = result_long
        elif ema_cross == "Bearish Cross":
            logger.info(f"Cruce de EMAs detectado: {ema_cross}. Preparando señal SHORT para {symbol}.")
            result_long, result_short = calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d)
            selected_result = result_short
    else:
        result_long, result_short = calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d)
        selected_result = None
        if result_long and result_short:
            selected_result = result_long if result_long[8] > result_short[8] else result_short
        elif result_long:
            selected_result = result_long
        elif result_short:
            selected_result = result_short

    if not selected_result:
        return False

    # Filtrar la señal si es necesario
    selected_result = filter_signal(selected_result, symbol)

    if not selected_result:
        return False

    # Obtener el sentimiento del mercado
    sentiment, sentiment_score = get_market_sentiment()
    if sentiment:
        logger.info(f"Sentimiento del mercado: {sentiment}, Puntuación: {sentiment_score}")

    entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength = selected_result

    # Enviar señal
    send_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross, sentiment=sentiment)

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

def get_symbol_data(symbol, client):
    logger.info(f"Obteniendo datos para {symbol}")
    candles = client.futures_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
    data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                          'quote_asset_volume', 'number_of_trades',
                                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                          'ignore'])
    for col in ['close', 'high', 'low', 'volume']:
        data[col] = data[col].astype(float)
    return data



def select_random_symbols(client):
    exchange_info = client.futures_exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')]
    random.shuffle(symbols)
    return symbols[:5]



def perform_trade_analysis():
    logger.info("Iniciando análisis de trading avanzado")
    symbol_memory = set()

    while True:
        try:
            # Analizar BTC y añadir el Market Cap
            btc_data_1h = get_btc_data(KLINE_INTERVAL)
            btc_data_1d = get_btc_data('1d')
            btc_data_1h = analyze_btc_market_cap(btc_data_1h)

            # Selección aleatoria de símbolos para futuros
            symbols = select_random_symbols()

            for symbol in symbols:
                if symbol in symbol_memory:
                    continue  # Evitar analizar el mismo símbolo repetidamente
                symbol_memory.add(symbol)
                
                try:
                    data = get_symbol_data(symbol)
                    if data is None:
                        logger.error(f"Error: Datos nulos obtenidos para {symbol}, omitiendo análisis.")
                        continue

                    # Analizar el símbolo aleatorio y añadir el análisis de Market Cap
                    data = analyze_random_symbol_market_cap(symbol, data)

                    if analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
                        logger.info(f"Se encontró una señal para {symbol}")
                        time.sleep(900)
                    else:
                        logger.info(f"No se encontró una señal adecuada para {symbol}")
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Error al analizar {symbol}: {e}")
                    continue

            logger.info("Ciclo completo, esperando antes de la siguiente iteración")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error en el ciclo principal: {str(e)}")
            time.sleep(60)



if __name__ == "__main__":
    thread = threading.Thread(target=perform_trade_analysis)
    thread.start()