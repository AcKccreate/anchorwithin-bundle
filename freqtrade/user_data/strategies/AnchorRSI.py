"""
AnchorRSI Strategy for Freqtrade
RSI + MACD crossover strategy for Kraken exchange.

Entry: RSI crosses above 30 + MACD bullish crossover
Exit:  RSI crosses below 70 + MACD bearish crossover
Trailing stop-loss: 5%
Take profit: 10%
"""

from freqtrade.strategy import IStrategy
import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from pandas import DataFrame


class AnchorRSI(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"

    # Take profit at 10% ROI
    minimal_roi = {
        "0": 0.10,
    }

    # Stop-loss at 5%
    stoploss = -0.05

    # Trailing stop-loss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Signal settings
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles needed before producing valid signals
    startup_candle_count: int = 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI (14-period)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # MACD (12, 26, 9)
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # RSI crosses above 30 (oversold recovery)
                qtpylib.crossed_above(dataframe["rsi"], 30)
                &
                # MACD is bullish (MACD line above signal line)
                (dataframe["macd"] > dataframe["macdsignal"])
                &
                # Volume sanity check
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # RSI crosses below 70 (overbought reversal)
                qtpylib.crossed_below(dataframe["rsi"], 70)
                &
                # MACD is bearish (MACD line below signal line)
                (dataframe["macd"] < dataframe["macdsignal"])
                &
                # Volume sanity check
                (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1

        return dataframe
