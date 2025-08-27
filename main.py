import discord
import asyncio
import datetime
import requests
import os, threading
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import MetaTrader5 as mt5
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))  # Render sẽ đặt PORT env var
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()


# ==============================
# Trend Tracker Logic - Improved with Sideway
# ==============================
class TrendTracker:
    def __init__(self, start_price, extreme_price):
        self.start_price = start_price
        self.high = max(start_price, extreme_price)
        self.low = min(start_price, extreme_price)
        self.total_trend = self.high - self.low
        self.last_price = start_price  # Có thể chỉnh thành extreme nếu giá hiện tại là extreme
        self.last_update_time = datetime.now(timezone.utc)
        self.reset_price = None
        self.pre_reset_trend = None

        if self.total_trend >= 10:
            self.trend = "up" if extreme_price > start_price else "down"
            self.extreme_price = extreme_price
        else:
            self.trend = "sideway"
            self.extreme_price = extreme_price  # For reference

    def get_trend_emoji(self):
        """Trả về emoji tương ứng với xu hướng"""
        if self.trend == "up":
            return "📈"
        elif self.trend == "down":
            return "📉"
        elif self.trend == "sideway":
            return "↔️"
        else:
            return "⏸️"

    def format_price_change(self, delta, minutes=15):
        """Format thông báo thay đổi giá"""
        if abs(delta) < 1:
            return f"⚪ {minutes}p: Ít biến động ({delta:+.1f}$)"
        elif delta > 0:
            return f"🟢 {minutes}p: +{delta:.1f}$"
        else:
            return f"🔴 {minutes}p: {delta:.1f}$"

    def update(self, price: float):
        messages = []

        # Delta 15p
        delta = price - self.last_price
        # Logic delta với hỗ trợ sideway
        if abs(delta) < 1:
            if self.trend == "up":
                messages.append(f"Giá Vàng ít biến động {delta:+.2f} USD, tổng tăng: {self.total_trend:.2f} USD")
            elif self.trend == "down":
                messages.append(f"Giá Vàng ít biến động {delta:+.2f} USD, tổng giảm: {self.total_trend:.2f} USD")
            elif self.trend == "sideway":
                messages.append(f"Giá Vàng ít biến động {delta:+.2f} USD")
            else:
                messages.append(f"Giá Vàng ít biến động {delta:+.2f} USD")
        elif delta > 0:
            if self.trend == "up":
                messages.append(f"Giá Vàng tăng {delta:.2f} USD, tổng tăng: {self.total_trend:.2f} USD")
            elif self.trend == "sideway":
                messages.append(f"Giá Vàng tăng {delta:.2f} USD")
            else:
                messages.append(f"Giá Vàng tăng {delta:.2f} USD")
        elif delta < 0:
            if self.trend == "down":
                messages.append(f"Giá Vàng giảm {abs(delta):.2f} USD, tổng giảm: {self.total_trend:.2f} USD")
            elif self.trend == "sideway":
                messages.append(f"Giá Vàng giảm {abs(delta):.2f} USD")
            else:
                messages.append(f"Giá Vàng giảm {abs(delta):.2f} USD")

        self.last_price = price

        # ========================
        # Logic xu hướng (thêm sideway)
        # ========================

        if self.trend == "sideway":
            updated = False
            if price > self.high:
                self.high = price
                updated = True
            if price < self.low:
                self.low = price
                updated = True
            self.total_trend = self.high - self.low
            if self.total_trend >= 10 and updated:
                if price == self.high:
                    self.trend = "up"
                    self.start_price = self.low
                    self.extreme_price = self.high
                    self.total_trend = self.high - self.low
                    messages.append(f"Giá Vàng tăng vượt 10 USD ,tổng tăng: {self.total_trend:.2f} USD")
                elif price == self.low:
                    self.trend = "down"
                    self.start_price = self.high
                    self.extreme_price = self.low
                    self.total_trend = self.start_price - self.extreme_price
                    messages.append(f"Giá Vàng giảm vượt 10 USD ,tổng giảm: {self.total_trend:.2f} USD")
            else:
                messages.append(f"Giá Vàng sideway, range tổng: {self.total_trend:.2f} USD")

        elif self.trend is None and self.reset_price is not None:
            if self.pre_reset_trend == "up":
                if price > self.extreme_price:
                    self.trend = "up"
                    self.start_price = self.reset_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    self.reset_price = None
                    messages = [f"Giá Vàng phá đỉnh cũ, tổng tăng: {self.total_trend:.2f} USD"]
                elif price < self.reset_price:
                    self.trend = "down"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    self.reset_price = None
                    messages = [f"Giá Vàng tiếp tục giảm, tổng giảm: {self.total_trend:.2f} USD"]
                else:
                    messages = [f"Giá Vàng ít biến động {delta:+.2f} USD, chưa xác định xu hướng mới"]

            elif self.pre_reset_trend == "down":
                if price < self.extreme_price:
                    self.trend = "down"
                    self.start_price = self.reset_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    self.reset_price = None
                    messages = [f"Giá Vàng phá đáy cũ, tổng giảm: {self.total_trend:.2f} USD"]
                elif price > self.reset_price:
                    self.trend = "up"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    self.reset_price = None
                    messages = [f"Giá Vàng tiếp tục tăng, tổng tăng: {self.total_trend:.2f} USD"]
                else:
                    messages = [f"Giá Vàng ít biến động {delta:+.2f} USD, chưa xác định xu hướng mới"]

        elif self.trend == "up":
            if price > self.extreme_price:
                self.extreme_price = price
                self.total_trend = self.extreme_price - self.start_price
                messages = [f"Giá Vàng tạo đỉnh mới, tổng tăng: {self.total_trend:.2f} USD"]
            else:
                pull_amt = self.extreme_price - price
                pull_pct = (pull_amt / (self.extreme_price - self.start_price)) * 100

                if pull_pct >= 100:
                    self.trend = "down"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    messages = [f"🤩 AN TOÀN! Giá Vàng đảo chiều, tổng giảm: {self.total_trend:.2f} USD"]
                elif pull_pct >= 40:
                    self.pre_reset_trend = "up"
                    self.trend = None
                    self.reset_price = price
                    old_total = self.total_trend
                    self.total_trend = 0
                    messages = [
                        f"🤩 AN TOÀN! Giá Vàng giảm {pull_amt:.2f} USD, Pullback {pull_pct:.2f}% sau chuỗi tăng: {old_total:.2f} USD"]
                else:
                    messages = [
                        f"Giá Vàng giảm {pull_amt:.2f} USD, Pullback {pull_pct:.2f}% sau chuỗi tăng: {self.total_trend:.2f} USD"]

        elif self.trend == "down":
            if price < self.extreme_price:
                self.extreme_price = price
                self.total_trend = self.start_price - self.extreme_price
                messages = [f"Giá Vàng tạo đáy mới, tổng giảm: {self.total_trend:.2f} USD"]
            else:
                pull_amt = price - self.extreme_price
                pull_pct = (pull_amt / (self.start_price - self.extreme_price)) * 100

                if pull_pct >= 100:
                    self.trend = "up"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    messages = [f"🤩 AN TOÀN! Giá Vàng đảo chiều, tổng tăng: {self.total_trend:.2f} USD"]
                elif pull_pct >= 40:
                    self.pre_reset_trend = "down"
                    self.trend = None
                    self.reset_price = price
                    old_total = self.total_trend
                    self.total_trend = 0
                    messages = [
                        f" 🤩 AN TOÀN! Giá Vàng tăng {pull_amt:.2f} USD, Pullback {pull_pct:.2f}% sau chuỗi giảm: {old_total:.2f} USD"]
                else:
                    messages = [
                        f"Giá Vàng tăng {pull_amt:.2f} USD, Pullback {pull_pct:.2f}% sau chuỗi giảm: {self.total_trend:.2f} USD"]

        return "\n".join(messages)

    def get_status_summary(self):
        """Trả về tóm tắt trạng thái hiện tại"""
        if self.trend == "sideway":
            return f"↔️ SIDEWAY: Range {self.total_trend:.1f}$ ({self.low:.1f}$ - {self.high:.1f}$)"
        elif self.trend:
            emoji = self.get_trend_emoji()
            return f"{emoji} {self.trend.upper()}: {self.start_price:.1f}$ → {self.extreme_price:.1f}$ ({self.total_trend:.1f}$)"
        elif self.reset_price:
            return f"⏸️ RESET tại {self.reset_price:.1f}$ (chờ xu hướng mới)"
        else:
            return "❓ Chưa khởi tạo"


# ==============================
# Discord Bot - Improved
# ==============================
# TOKEN = os.getenv("DISCORD_TOKEN")  # Lấy token từ biến môi trường

CHANNEL_ID = 1406848822860320828  # thay bằng channel ID của bạn


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

tracker = None
waiting_for_init = True

if not mt5.initialize():
    logger.error(f"❌ Kết nối MT5 thất bại: {mt5.last_error()}")
    raise RuntimeError("Không thể kết nối tới MT5")

symbol = "XAUUSDm"

# async def get_gold_price():
#     """Lấy giá vàng từ API - không fallback giá ngẫu nhiên"""
#     try:
#         # API thật - thay bằng provider giá vàng của bạn
#         url = "https://api.metals.live/v1/spot/gold"
#         response = requests.get(url, timeout=10)
#         if response.status_code == 200:
#             data = response.json()
#             return data[0]["price"]  # Giá USD/oz
#         else:
#             raise Exception(f"API returned status {response.status_code}")
#     except Exception as e:
#         logger.error(f"❌ Không thể lấy giá vàng: {e}")
#         raise Exception(f"Lỗi lấy giá: {str(e)}")

def get_gold_price():
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise Exception("Không thể lấy dữ liệu từ MT5")
    return tick.bid  # hoặc tick.ask/last


async def price_loop_simple(channel):
    """Phiên bản đơn giản và ổn định nhất"""
    global tracker
    await client.wait_until_ready()

    processed_times = set()  # Lưu các thời điểm đã xử lý

    while not client.is_closed():
        try:
            now = datetime.now(timezone.utc) + timedelta(hours=7)  # giờ VN
            weekday = now.weekday()
            hour = now.hour
            minute = now.minute

            # Thị trường mở cửa
            market_open = (
                    (weekday == 0 and hour >= 5) or  # Thứ 2 từ 5h
                    (0 < weekday < 5) or  # Thứ 3-6
                    (weekday == 5 and hour < 4)  # Thứ 7 đến 4h
            )

            # Tạo key thời gian duy nhất cho mỗi slot 15 phút
            time_slot = f"{now.date()}_{hour:02d}_{(minute // 15) * 15:02d}"

            if (market_open and tracker and
                    minute % 15 == 0 and  # Đúng phút tròn
                    time_slot not in processed_times):  # Chưa xử lý

                try:
                    price = get_gold_price()
                    msg = tracker.update(price)

                    if 6 <= hour <= 23:
                        await channel.send(msg)
                        logger.info(f"✅ Thông báo gửi lúc: {now.strftime('%d/%m/%Y %H:%M:%S')}")
                    else:
                        logger.info(f"[{now.strftime('%H:%M')}] {msg}")

                    processed_times.add(time_slot)

                    # Dọn dẹp processed_times cũ (giữ lại 24h)
                    if len(processed_times) > 100:
                        processed_times.clear()

                except Exception as price_error:
                    logger.error(f"Lỗi lấy giá vàng: {price_error}")
                    if 6 <= hour <= 23:
                        await channel.send(f"❌ Lỗi lấy giá: {price_error}")

            # Luôn sleep 30 giây để kiểm tra thường xuyên
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error in price_loop_simple: {e}")
            await asyncio.sleep(60)


@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🤖 Gold Tracker Bot",
            description="Bot đã khởi động! Nhập giá khởi tạo:",
            color=0xFFD700
        )
        embed.add_field(name="Format", value="`start=xxxx extreme=xxxx`", inline=False)
        embed.add_field(name="Ví dụ", value="`start=2650 extreme=2680`", inline=False)
        await channel.send(embed=embed)

        # Bắt đầu vòng lặp
        client.loop.create_task(price_loop_simple(channel))
    else:
        logger.error(f"Cannot find channel with ID: {CHANNEL_ID}")


@client.event
async def on_message(message):
    global tracker, waiting_for_init

    if message.author == client.user:
        return

    # Lệnh trạng thái
    if message.content.lower() == "!status" and tracker:
        status = tracker.get_status_summary()
        await message.channel.send(f"📊 **Trạng thái hiện tại:**\n{status}")
        return

    # Khởi tạo tracker
    if waiting_for_init:
        if "start=" in message.content and "extreme=" in message.content:
            try:
                # Parse input linh hoạt hơn
                content = message.content.replace(",", " ").replace("  ", " ")
                parts = content.split()

                start = None
                extreme = None

                for part in parts:
                    if "start=" in part:
                        start = float(part.split("=")[1])
                    elif "extreme=" in part:
                        extreme = float(part.split("=")[1])

                if start is not None and extreme is not None:
                    tracker = TrendTracker(start, extreme)
                    waiting_for_init = False

                    embed = discord.Embed(
                        title="✅ Tracker đã khởi tạo",
                        description=tracker.get_status_summary(),
                        color=0x00FF00
                    )
                    embed.add_field(name="Lệnh khả dụng", value="`!status` - Xem trạng thái\n`!reset` - Reset tracker",
                                    inline=False)
                    await message.channel.send(embed=embed)
                else:
                    raise ValueError("Missing start or extreme value")

            except Exception as e:
                await message.channel.send(f"❌ Lỗi format. Sử dụng: `start=2650 extreme=2680`\nLỗi: {str(e)}")
    else:
        # Reset tracker
        if message.content.lower() == "!reset":
            tracker = None
            waiting_for_init = True
            await message.channel.send("🔄 Tracker đã reset! Nhập giá khởi tạo mới.")


# Chạy bot với xử lý lỗi
if __name__ == "__main__":
    logger.info("🚀 Bot đang khởi động trên Render...")
    try:
        client.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
