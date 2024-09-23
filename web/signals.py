import pandas as pd
import numpy as np
import ta
import logging
import threading
import time
import random
from binance.client import Client as FuturesClient
from .models import UserProfile

# Configuración
KLINE_INTERVAL = '1h'
KLINE_LIMIT = 100
ORDER_BOOK_LIMIT = 100

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Funciones de Conexión
def get_client_from_user(user):
    user_profile = UserProfile.objects.get(user=user)
    api_key = user_profile.get_api_key()
    api_secret = user_profile.get_api_secret()
    return FuturesClient(api_key, api_secret)

# Funciones para obtener datos de libros de órdenes y calcular precios
def get_order_book(client, symbol):
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
    return sum(price * size for price, size in levels) / total_volume

def get_weighted_prices_from_order_book(client, symbol):
    bids, asks = get_order_book(client, symbol)
    if not bids or not asks:
        return None, None
    weighted_buy_price = calculate_weighted_average_price(bids)
    weighted_sell_price = calculate_weighted_average_price(asks)
    return weighted_buy_price, weighted_sell_price

# Cálculo de indicadores técnicos
def calculate_emas(data, short_period=9, long_period=26):
    data['ema_short'] = ta.trend.ema_indicator(data['close'], window=short_period)
    data['ema_long'] = ta.trend.ema_indicator(data['close'], window=long_period)
    return data

def detect_ema_cross(data):
    if data['ema_short'].iloc[-2] < data['ema_long'].iloc[-2] and data['ema_short'].iloc[-1] > data['ema_long'].iloc[-1]:
        return "Bullish Cross"
    elif data['ema_short'].iloc[-2] > data['ema_long'].iloc[-2] and data['ema_short'].iloc[-1] < data['ema_long'].iloc[-1]:
        return "Bearish Cross"
    return None

# Función para analizar oportunidades de trading y detectar señales
def analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
    data = calculate_emas(data)
    data = calculate_ichimoku(data)
    ema_cross = detect_ema_cross(data)
    
    if ema_cross:
        return ema_cross
    
    # Añadir análisis adicional con Fibonacci, RSI y MACD
    fib_levels = calculate_fibonacci_levels(data)
    rsi = data['rsi'].iloc[-1]
    macd = data['macd'].iloc[-1]

    logger.info(f"Fibonacci levels for {symbol}: {fib_levels}")
    logger.info(f"RSI for {symbol}: {rsi}")
    logger.info(f"MACD for {symbol}: {macd}")
    
    # Filtrar señales basadas en el análisis
    if ema_cross == "Bullish Cross" and rsi < 70:
        return "Buy"
    elif ema_cross == "Bearish Cross" and rsi > 30:
        return "Sell"
    else:
        return None

# Funciones auxiliares de indicadores técnicos
def calculate_ichimoku(data):
    ichimoku = ta.trend.IchimokuIndicator(data['high'], data['low'], window1=9, window2=26, window3=52)
    data['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
    data['kijun_sen'] = ichimoku.ichimoku_base_line()
    data['senkou_span_a'] = ichimoku.ichimoku_a()
    data['senkou_span_b'] = ichimoku.ichimoku_b()
    data['chikou_span'] = data['close'].shift(-26)
    data['ichimoku_cross'] = np.where(
        (data['tenkan_sen'].shift(1) < data['kijun_sen'].shift(1)) & (data['tenkan_sen'] > data['kijun_sen']),
        'Bullish Cross', 
        np.where((data['tenkan_sen'].shift(1) > data['kijun_sen'].shift(1)) & (data['tenkan_sen'] < data['kijun_sen']),
                 'Bearish Cross', 'No Cross')
    )
    return data

def calculate_vwap(data):
    return ta.volume.volume_weighted_average_price(data['high'], data['low'], data['close'], data['volume'])

def calculate_fibonacci_levels(data):
    low = data['low'].min()
    high = data['high'].max()
    diff = high - low
    return {
        '23.6%': high - 0.236 * diff,
        '38.2%': high - 0.382 * diff,
        '50%': high - 0.5 * diff,
        '61.8%': high - 0.618 * diff,
        '100%': high
    }


def calculate_btc_indicators(btc_data):
    btc_data['vwap'] = calculate_vwap(btc_data)
    btc_data['atr'] = ta.volatility.average_true_range(btc_data['high'], btc_data['low'], btc_data['close'])
    btc_data['ema_50'] = ta.trend.ema_indicator(btc_data['close'], window=50)
    btc_data['ema_200'] = ta.trend.ema_indicator(btc_data['close'], window=200)
    btc_data['rsi'] = ta.momentum.rsi(btc_data['close'])
    btc_data['mfi'] = ta.volume.money_flow_index(btc_data['high'], btc_data['low'], btc_data['close'], btc_data['volume'])
    btc_data['macd'] = ta.trend.macd_diff(btc_data['close'])
    calculate_ichimoku(btc_data)
    return btc_data

def get_market_sentiment(client):
    try:
        btc_stats = client.futures_ticker(symbol='BTCUSDT')
        price_change_percent = float(btc_stats['priceChangePercent'])
        volume = float(btc_stats['volume'])
        sentiment_score = price_change_percent * volume
        sentiment = 'Bullish' if price_change_percent > 0 else 'Bearish' if price_change_percent < 0 else 'Neutral'
        logger.info(f"Sentimiento del mercado calculado: {sentiment} (Puntaje: {sentiment_score:.2f})")
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


# Funciones para obtener datos de mercado
def get_btc_data(client, interval):
    candles = client.futures_klines(symbol='BTCUSDT', interval=interval, limit=KLINE_LIMIT)
    btc_data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    btc_data['close'] = btc_data['close'].astype(float)
    return calculate_btc_indicators(btc_data)

def get_symbol_data(client, symbol):
    candles = client.futures_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
    data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['close'] = data['close'].astype(float)
    return data

def select_random_symbols(client):
    exchange_info = client.futures_exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')]
    random.shuffle(symbols)
    return symbols[:5]

# Enviar señales
def send_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross=None, sentiment=None):
    """
    Envía una señal de trading. Se puede integrar con Telegram o la vista web.
    """
    # Verificar si hay valores duplicados o nulos
    unique_values = {entry1, entry2, stop_loss, tp1, tp2, tp3, tp4}
    if None in unique_values or len(unique_values) != 7:
        logger.error(f"Error en señal: No deben haber valores repetidos o nulos en Entry Points, Stop Loss y Take Profits.")
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

    # Agregar lógica para enviar la señal a la vista del dashboard.
    logger.info(f"Señal generada para {symbol}: {message}")



# Configuración del logger
logger = logging.getLogger(__name__)

def perform_trade_analysis():
    """
    Función principal para el análisis de trading. Controla los ciclos de análisis y la lógica para evitar 
    la repetición de análisis sobre los mismos símbolos y el uso excesivo de la API.
    """
    logger.info("Iniciando análisis de trading avanzado")
    
    # Memoria de símbolos analizados
    symbol_memory = set()
    cycle_count = 0  # Contador de ciclos

    # Ciclo principal de análisis
    while True:
        try:
            # Limpiar la memoria cada 10 ciclos
            if cycle_count >= 10:
                symbol_memory.clear()
                logger.info("Memoria de símbolos limpiada.")
                cycle_count = 0

            # Obtener datos de BTC en intervalos de 1 hora y 1 día
            logger.info("Obteniendo datos de BTC en intervalos de 1 hora y 1 día.")
            btc_data_1h = get_btc_data(KLINE_INTERVAL)
            btc_data_1d = get_btc_data('1d')
            
            # Selección aleatoria de símbolos
            symbols = select_random_symbols()
            logger.info(f"Símbolos seleccionados para el análisis: {symbols}")

            # Análisis por cada símbolo
            for symbol in symbols:
                if symbol in symbol_memory:
                    logger.info(f"Símbolo {symbol} ya analizado en este ciclo, se omite.")
                    continue  # Evitar analizar el mismo símbolo repetidamente
                symbol_memory.add(symbol)  # Añadir el símbolo a la memoria
                
                try:
                    # Obtener datos del símbolo
                    logger.info(f"Obteniendo datos del símbolo {symbol}")
                    data = get_symbol_data(symbol)
                    if data is None:
                        logger.error(f"Error: Datos nulos obtenidos para {symbol}, omitiendo análisis.")
                        continue

                    # Análisis del trade
                    logger.info(f"Iniciando análisis para {symbol}")
                    signal = analyze_trade(symbol, data, btc_data_1h, btc_data_1d)
                    if signal:
                        logger.info(f"Se encontró una señal para {symbol}: {signal}")
                        time.sleep(30)  # Mayor tiempo de espera si se encuentra una señal
                    else:
                        logger.info(f"No se encontró una señal adecuada para {symbol}")
                        time.sleep(5)

                except ValueError as ve:
                    logger.error(f"Error en el análisis de {symbol}: {ve}")
                except Exception as e:
                    logger.error(f"Error inesperado al analizar {symbol}: {e}")
                    continue

            logger.info("Ciclo completo, esperando antes de la siguiente iteración.")
            cycle_count += 1  # Incrementar el contador de ciclos
            time.sleep(20)
            
        except Exception as e:
            logger.error(f"Error en el ciclo principal: {str(e)}")
            time.sleep(60)



if __name__ == "__main__":
    # Iniciar el análisis de trading en un hilo separado
    thread = threading.Thread(target=perform_trade_analysis)
    thread.start()
