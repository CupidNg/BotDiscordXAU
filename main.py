import discord
import asyncio
import datetime
import requests
import logging
from datetime import datetime, timezone
import os
from discord.ext import commands

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
TOKEN = os.getenv("DISCORD_TOKEN")  # Lấy token từ biến môi trường
CHANNEL_ID = 1406848822860320828  # thay bằng channel ID của bạn

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

tracker = None
waiting_for_init = True


async def get_gold_price():
    """Lấy giá vàng từ API - không fallback giá ngẫu nhiên"""
    try:
        # API thật - thay bằng provider giá vàng của bạn
        url = "https://api.metals.live/v1/spot/gold"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data[0]["price"]  # Giá USD/oz
        else:
            raise Exception(f"API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Không thể lấy giá vàng: {e}")
        raise Exception(f"Lỗi lấy giá: {str(e)}")


async def price_loop(channel):
    """Vòng lặp chính - cải tiến xử lý lỗi"""
    global tracker
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            now = datetime.now(timezone.utc) + timedelta(hours=7)  # giờ VN
            weekday = now.weekday()
            hour = now.hour
            minute = now.minute

            # Thị trường mở cửa (cải tiến logic)
            market_open = (
                    (weekday == 0 and hour >= 5) or  # Thứ 2 từ 5h
                    (0 < weekday < 5) or  # Thứ 3-6
                    (weekday == 5 and hour < 4)  # Thứ 7 đến 4h
            )

            if market_open and tracker:
                # Đợi đến phút chia hết cho 15
                wait_minutes = (15 - (minute % 15)) % 15
                if wait_minutes == 0:
                    wait_minutes = 15

                await asyncio.sleep(wait_minutes * 60)

                # Lấy giá và cập nhật
                try:
                    price = await get_gold_price()
                    msg = tracker.update(price)

                    # Chỉ gửi trong giờ hoạt động
                    current_time = datetime.now(timezone.utc) + timedelta(hours=7)
                    if 6 <= current_time.hour <= 23:  # Mở rộng giờ hoạt động
                        await channel.send(msg)
                    else:
                        logger.info(f"[{current_time.strftime('%H:%M')}] {msg}")

                except Exception as price_error:
                    logger.error(f"Lỗi lấy giá vàng: {price_error}")
                    current_time = datetime.now(timezone.utc) + timedelta(hours=7)
                    if 6 <= current_time.hour <= 23:
                        await channel.send(f"❌ Không lấy được giá vàng: {price_error}. Đang thử lại...")
                    # Đợi 2 phút rồi thử lại thay vì đợi 15 phút
                    await asyncio.sleep(120)
            else:
                await asyncio.sleep(300)  # Kiểm tra lại sau 5 phút

        except Exception as e:
            logger.error(f"Error in price_loop: {e}")
            await asyncio.sleep(60)  # Đợi 1 phút rồi thử lại


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
        client.loop.create_task(price_loop(channel))
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
    try:
        client.run(TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")