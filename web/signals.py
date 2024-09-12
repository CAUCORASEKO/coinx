import pandas as pd
import numpy as np
import ta
import os
import random
import logging
import threading
import time
import requests
from binance.client import Client as FuturesClient

# Configuración centralizada
KLINE_INTERVAL = '1h'
KLINE_LIMIT = 100
ORDER_BOOK_LIMIT = 100  # Cambiado a 100 para ser consistente con KLINE_LIMIT

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


API_KEY = 'oPHdqnlj2669QZBdTasg9Sb7n8C6bW5HRs72USqOZMmcNSaeguJ8zLQNunXlWZ0b'
API_SECRET = 'FRqQJudUsEsrm4n6UGpcrkPGHtaRehMZwPzNsJLEOBEG7DeIH8mDMXALfLLR30jn'


client = FuturesClient(API_KEY, API_SECRET)

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
    """
    Calcula el precio promedio ponderado basado en las órdenes del libro.
    :param levels: Lista de tuplas (precio, tamaño).
    :return: Precio promedio ponderado.
    """
    total_volume = sum(size for price, size in levels)
    if total_volume == 0:
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
    try:
        for _ in range(retries):
            bids, asks = get_order_book(symbol)
            
            if not bids or not asks:
                logger.error(f"Error: bids o asks están vacíos para el símbolo {symbol}. Reintentando...")
                time.sleep(2)  # Espera breve antes de intentar de nuevo
                continue  # Reintenta si los datos están vacíos
            
            # Verificar si el volumen es significativo
            if not is_volume_significant(bids) or not is_volume_significant(asks):
                logger.warning(f"Volumen insuficiente para {symbol}. Reintentando...")
                time.sleep(2)  # Espera breve antes de intentar de nuevo
                continue
            
            # Calcula los precios ponderados de compra y venta
            weighted_buy_price = calculate_weighted_average_price(bids)
            weighted_sell_price = calculate_weighted_average_price(asks)
            
            if weighted_buy_price is None or weighted_sell_price is None:
                logger.error(f"No se pudieron calcular los precios ponderados para {symbol}. Reintentando...")
                time.sleep(2)  # Espera breve antes de intentar de nuevo
                continue  # Reintenta si no se pueden calcular
            
            logger.info(f"Precios ponderados calculados para {symbol} -> Compra: {weighted_buy_price:.2f}, Venta: {weighted_sell_price:.2f}")
            return weighted_buy_price, weighted_sell_price
        
        logger.error(f"Error: No se pudo obtener precios ponderados para {symbol} después de {retries} intentos.")
        return None, None
    
    except Exception as e:
        logger.error(f"Error al obtener precios ponderados para {symbol}: {str(e)}", exc_info=True)
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

def calculate_weighted_average_price(levels):
    total_volume = sum(size for price, size in levels)
    if total_volume == 0:
        return None
    weighted_avg_price = sum(price * size for price, size in levels) / total_volume
    return weighted_avg_price

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

def get_market_sentiment():
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
    logger.info(f"Identificados desde el libro de órdenes -> Soporte: {support:.2f}, Resistencia: {resistance:.2f}")

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

    # Filtrar señales por sobrecompra/sobreventa usando RSI y MFI
    if data['rsi'].iloc[-1] > 80 or data['mfi'].iloc[-1] > 80:
        logger.info(f"Señal para {symbol} (Long) filtrada por condiciones de sobrecompra.")
        return None, None
    if data['rsi'].iloc[-1] < 20 or data['mfi'].iloc[-1] < 20:
        logger.info(f"Señal para {symbol} (Short) filtrada por condiciones de sobreventa.")
        return None, None

    # Puntos de entrada y calidad
    entry_long, quality_long = find_entry_point(symbol, data, bids, asks, "up", support, resistance)
    entry_short, quality_short = find_entry_point(symbol, data, bids, asks, "down", support, resistance)

    entry_long, entry_long_2, stop_loss_long, take_profits_long, signal_strength_long = process_entry(entry_long, data, "up")
    entry_short, entry_short_2, stop_loss_short, take_profits_short, signal_strength_short = process_entry(entry_short, data, "down")

    return prepare_return(entry_long, entry_long_2, stop_loss_long, take_profits_long, signal_strength_long, "Long"), \
           prepare_return(entry_short, entry_short_2, stop_loss_short, take_profits_short, signal_strength_short, "Short")


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
    Evalúa la calidad de un punto de entrada basado en indicadores y perfiles de volumen.
    """
    price_to_vwap = abs(price - vwap) / vwap
    atr_factor = abs(price - vwap) / atr
    volume_at_price = volume_profile.get(price, 0)
    
    if trend == "up":
        return (
            (price > tenkan_sen) * 0.7 +
            (price > kijun_sen) * 0.7 +
            (price > ema_50) * 0.7 +
            (20 < rsi < 80) * 1.2 +  
            (macd > 0) * 1.0 +
            (1 - price_to_vwap) * 1.0 +  
            (price > tenkan_sen) * 0.7 +
            (price > kijun_sen) * 0.7 +
            (price > senkou_span_a) * 0.7 +
            (price > senkou_span_b) * 0.7 +
            (atr_factor < 1.0) * 1.0 +  
            (volume_at_price) * 1.0  
        )
    else:
        return (
            (price < tenkan_sen) * 0.7 +
            (price < kijun_sen) * 0.7 +
            (price < ema_50) * 0.7 +
            (20 < rsi < 80) * 1.2 +  
            (macd < 0) * 1.0 +
            (1 - price_to_vwap) * 1.0 +  
            (price < tenkan_sen) * 0.7 +
            (price < kijun_sen) * 0.7 +
            (price < senkou_span_a) * 0.7 +
            (price < senkou_span_b) * 0.7 +
            (atr_factor < 1.0) * 1.0 +  
            (volume_at_price) * 1.0  
        )


def find_entry_point(symbol, data, bids, asks, trend, support, resistance):
    """
    Función para encontrar puntos de entrada más precisos tanto en posiciones long como short.
    Se ajusta según el soporte/resistencia, el ATR, y la fuerza de los bids y asks.
    """
    logger.info(f"Buscando puntos de entrada {trend} para {symbol}")

    # Obtener los precios ponderados del libro de órdenes
    weighted_buy_price, weighted_sell_price = get_weighted_prices_from_order_book(symbol)

    if weighted_buy_price is None or weighted_sell_price is None:
        logger.error(f"Los precios ponderados para {symbol} no se pudieron obtener correctamente. Saltando...")
        return None, None  # Si no se obtienen precios válidos, no intentamos calcular puntos de entrada

    # Calcular el ATR para ajustar los puntos de entrada según la volatilidad
    atr = data['atr'].iloc[-1]

    # Calcular la fuerza de los compradores (bids) y vendedores (asks)
    force_bulls, force_bears = calculate_force(bids, asks)

    if trend == "up" and force_bulls > 0.55:  # Solo si la fuerza de los compradores es alta
        # Lógica para trades long (al alza)
        entry_point_1 = max(support, weighted_buy_price - atr)  # Entrada cerca de soporte ajustada con ATR
        entry_point_2 = max(support, weighted_buy_price - (atr * 1.5))  # Ajuste adicional si hay más volatilidad
    elif trend == "down" and force_bears > 0.55:  # Solo si la fuerza de los vendedores es alta
        # Lógica para trades short (a la baja)
        entry_point_1 = min(resistance, weighted_sell_price + atr)  # Entrada cerca de resistencia ajustada con ATR
        entry_point_2 = min(resistance, weighted_sell_price + (atr * 1.5))  # Ajuste adicional si hay más volatilidad
    else:
        logger.info(f"La fuerza de mercado no soporta la entrada en {symbol}. Omisión del trade.")
        return None, None

    logger.info(f"Puntos ajustados de entrada - Entry Point 1: {entry_point_1:.4f}, Entry Point 2: {entry_point_2:.4f}")

    # Evaluar la calidad de estos puntos de entrada basándose en indicadores técnicos y el perfil de volumen
    volume_profile = calculate_volume_profile(data)

    # Evaluar la calidad del punto de entrada
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
            volume_profile=volume_profile
        )

    # Calcular la calidad de los puntos de entrada
    quality_entry_point_1 = entry_quality(entry_point_1)
    quality_entry_point_2 = entry_quality(entry_point_2)

    logger.info(f"Calidad de Entry Point 1: {quality_entry_point_1:.2f}, Calidad de Entry Point 2: {quality_entry_point_2:.2f}")

    # Ajustar el umbral de calidad según la volatilidad
    quality_threshold = 4.0 if atr < data['close'].mean() * 0.01 else 3.5

    # Filtrar las entradas si no cumplen el umbral de calidad
    if quality_entry_point_1 < quality_threshold:
        logger.info(f"Entry Point 1 no cumple con el umbral de calidad. Se omite.")
        entry_point_1 = None

    if quality_entry_point_2 < quality_threshold:
        logger.info(f"Entry Point 2 no cumple con el umbral de calidad. Se omite.")
        entry_point_2 = None

    # Devolver el mejor punto de entrada si ambos son válidos
    if entry_point_1 and entry_point_2:
        return (entry_point_1, entry_point_2) if quality_entry_point_1 >= quality_entry_point_2 else (entry_point_2, entry_point_1)
    elif entry_point_1:
        return entry_point_1, None
    elif entry_point_2:
        return entry_point_2, None
    else:
        logger.info(f"No se encontraron puntos de entrada válidos para {symbol}.")
        return None, None




def adjust_entry_point(entry_price, data, trend):
    atr = data['atr'].iloc[-1]
    if trend == "up":
        adjusted_entry = entry_price + atr * 0.1
    elif trend == "down":
        adjusted_entry = entry_price - atr * 0.1
    else:
        adjusted_entry = entry_price
    return adjusted_entry

def calculate_stop_loss_take_profit(entry_price, data, trend):
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

def generate_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross=None, sentiment=None):
    unique_values = {entry1, entry2, stop_loss, tp1, tp2, tp3, tp4}
    if len(unique_values) != 7:
        logger.error(f"Error en señal: No deben haber valores repetidos en Entry Points, Stop Loss y Take Profits.")
        return

    # Devolver las señales en un formato fácil de procesar en la vista del dashboard
    signal = {
        "symbol": symbol,
        "type": signal_type,
        "entry_1": entry1,
        "entry_2": entry2,
        "stop_loss": stop_loss,
        "take_profits": [tp1, tp2, tp3, tp4],
        "strength": signal_strength,
        "ema_cross": ema_cross,
        "sentiment": sentiment
    }
    return signal



def analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
    data = calculate_emas(data)
    ema_cross = detect_ema_cross(data)

    if ema_cross:
        result_long, result_short = calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d)
        selected_result = result_long if ema_cross == "Bullish Cross" else result_short
    else:
        result_long, result_short = calculate_entry_stop_take(symbol, data, btc_data_1h, btc_data_1d)
        selected_result = result_long if result_long and (not result_short or result_long[8] > result_short[8]) else result_short

    if not selected_result:
        return None

    # Aplicar filtro de señal
    selected_result = filter_signal(selected_result, symbol)
    if not selected_result:
        return None

    # Obtener el sentimiento del mercado
    sentiment, sentiment_score = get_market_sentiment()
    entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength = selected_result

    # Enviar señal (modificada para devolver en lugar de enviar)
    return generate_signal(symbol, entry1, entry2, stop_loss, tp1, tp2, tp3, tp4, signal_type, signal_strength, ema_cross, sentiment=sentiment)



def get_btc_data(interval):
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

def get_symbol_data(symbol):
    logger.info(f"Obteniendo datos para {symbol}")
    candles = client.futures_klines(symbol=symbol, interval=KLINE_INTERVAL, limit=KLINE_LIMIT)
    data = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                          'quote_asset_volume', 'number_of_trades',
                                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                          'ignore'])
    for col in ['close', 'high', 'low', 'volume']:
        data[col] = data[col].astype(float)
    return data

def select_random_symbols():
    exchange_info = client.futures_exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')]
    random.shuffle(symbols)
    return symbols[:5]

def get_trading_signals():
    logger.info("Obteniendo señales de trading")
    signals = []
    btc_data_1h = get_btc_data(KLINE_INTERVAL)
    btc_data_1d = get_btc_data('1d')
    symbols = select_random_symbols()

    for symbol in symbols:
        data = get_symbol_data(symbol)
        signal = analyze_trade(symbol, data, btc_data_1h, btc_data_1d)
        if signal:
            signals.append(signal)

    return signals  # send signals 


def perform_trade_analysis():
    logger.info("Iniciando análisis de trading")
    symbol_memory = set()

    while True:
        try:
            btc_data_1h = get_btc_data(KLINE_INTERVAL)
            btc_data_1d = get_btc_data('1d')
            symbols = select_random_symbols()

            for symbol in symbols:
                if symbol in symbol_memory:
                    continue  # Evitar analizar el mismo símbolo repetidamente
                symbol_memory.add(symbol)
                try:
                    data = get_symbol_data(symbol)
                    if analyze_trade(symbol, data, btc_data_1h, btc_data_1d):
                        logger.info(f"Se encontró una señal para {symbol}")
                        time.sleep(900)
                    else:
                        logger.info(f"No se encontró una señal adecuada para {symbol}")
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Error al analizar {symbol}: {e}")

            logger.info("Esperando antes de la próxima iteración completa")
            time.sleep(20)
        except Exception as e:
            logger.error(f"Error en el ciclo principal: {e}")
            time.sleep(60)

if __name__ == "__main__":
    thread = threading.Thread(target=perform_trade_analysis)
    thread.start()
