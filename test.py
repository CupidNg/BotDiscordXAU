import MetaTrader5 as mt5
import logging

logger = logging.getLogger(__name__)

if not mt5.initialize():
    logger.error(f"❌ Kết nối MT5 thất bại: {mt5.last_error()}")
    raise RuntimeError("Không thể kết nối tới MT5")

symbol = "XAUUSDm"

def get_gold_price():
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise Exception("Không thể lấy dữ liệu từ MT5")
    return tick.bid  # hoặc tick.ask/last

# --- Demo gọi thử ---
if __name__ == "__main__":
    try:
        price = get_gold_price()
        print("Giá vàng hiện tại:", price)
    finally:
        mt5.shutdown()
