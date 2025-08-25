class TrendTracker:
    def __init__(self, start_price, extreme_price):
        self.start_price = start_price
        self.high = max(start_price, extreme_price)
        self.low = min(start_price, extreme_price)
        self.total_trend = self.high - self.low
        self.last_price = start_price
        self.last_update_time = datetime.datetime.utcnow()
        self.reset_price = None
        self.pre_reset_trend = None

        if self.total_trend >= 10:
            self.trend = "up" if extreme_price > start_price else "down"
            self.extreme_price = extreme_price
        else:
            self.trend = "sideway"
            self.extreme_price = extreme_price

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

    def update(self, price: float):
        messages = []
        delta = price - self.last_price

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
                    messages.append(
                        f"📈 Giá XAU: {price:.0f}, tăng {delta:.0f}$, VƯỢT KHỎI SIDEWAY → Tổng tăng: {self.total_trend:.0f}$")
                elif price == self.low:
                    self.trend = "down"
                    self.start_price = self.high
                    self.extreme_price = self.low
                    self.total_trend = self.start_price - self.extreme_price
                    messages.append(
                        f"📉 Giá XAU: {price:.0f}, giảm {abs(delta):.0f}$, VƯỢT KHỎI SIDEWAY → Tổng giảm: {self.total_trend:.0f}$")
            else:
                if abs(delta) < 1:
                    messages.append(f"↔️ Giá XAU: {price:.0f}, sideway ({delta:+.1f}$), Range: {self.total_trend:.0f}$")
                elif delta > 0:
                    messages.append(f"↗️ Giá XAU: {price:.0f}, tăng {delta:.0f}$, Range: {self.total_trend:.0f}$")
                else:
                    messages.append(f"↘️ Giá XAU: {price:.0f}, giảm {abs(delta):.0f}$, Range: {self.total_trend:.0f}$")

        elif self.trend is None and self.reset_price is not None:
            if self.pre_reset_trend == "up":
                if price > self.extreme_price:
                    self.trend = "up"
                    self.start_price = self.reset_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    self.reset_price = None
                    messages = [f"🚀 Giá XAU: {price:.0f}, PHÁ ĐỈNH → Tổng tăng: {self.total_trend:.0f}$"]
                elif price < self.reset_price:
                    self.trend = "down"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    self.reset_price = None
                    messages = [f"💥 Giá XAU: {price:.0f}, THỦNG PULLBACK → Tổng giảm: {self.total_trend:.0f}$"]
                else:
                    if abs(delta) < 1:
                        messages = [f"⏸️ Giá XAU: {price:.0f}, sideway ({delta:+.1f}$), chờ xu hướng mới"]
                    else:
                        messages = [
                            f"⏸️ Giá XAU: {price:.0f}, {'+' if delta > 0 else ''}{delta:.0f}$, chờ xu hướng mới"]

            elif self.pre_reset_trend == "down":
                if price < self.extreme_price:
                    self.trend = "down"
                    self.start_price = self.reset_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    self.reset_price = None
                    messages = [f"🔻 Giá XAU: {price:.0f}, PHÁ ĐÁY → Tổng giảm: {self.total_trend:.0f}$"]
                elif price > self.reset_price:
                    self.trend = "up"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    self.reset_price = None
                    messages = [f"🚀 Giá XAU: {price:.0f}, VƯỢT PULLBACK → Tổng tăng: {self.total_trend:.0f}$"]
                else:
                    if abs(delta) < 1:
                        messages = [f"⏸️ Giá XAU: {price:.0f}, sideway ({delta:+.1f}$), chờ xu hướng mới"]
                    else:
                        messages = [
                            f"⏸️ Giá XAU: {price:.0f}, {'+' if delta > 0 else ''}{delta:.0f}$, chờ xu hướng mới"]

        elif self.trend == "up":
            if price > self.extreme_price:
                self.extreme_price = price
                self.total_trend = self.extreme_price - self.start_price
                messages = [f"🔥 Giá XAU: {price:.0f}, tăng {delta:.0f}$, ĐỈNH MỚI → Tổng tăng: {self.total_trend:.0f}$"]
            else:
                pull_amt = self.extreme_price - price
                pull_pct = (pull_amt / (self.extreme_price - self.start_price)) * 100

                if pull_pct >= 100:
                    self.trend = "down"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.start_price - self.extreme_price
                    messages = [f"🤩 Giá XAU: {price:.0f}, ĐẢO CHIỀU AN TOÀN → Tổng giảm: {self.total_trend:.0f}$"]
                elif pull_pct >= 40:
                    self.pre_reset_trend = "up"
                    self.trend = None
                    self.reset_price = price
                    old_total = self.total_trend
                    self.total_trend = 0
                    messages = [
                        f"🤩 Giá XAU: {price:.0f}, giảm {pull_amt:.0f}$, Pullback {pull_pct:.0f}% AN TOÀN (Tổng tăng cũ: {old_total:.0f}$)"]
                else:
                    messages = [
                        f"📉 Giá XAU: {price:.0f}, giảm {pull_amt:.0f}$, Pullback {pull_pct:.0f}% → Tổng tăng: {self.total_trend:.0f}$"]

        elif self.trend == "down":
            if price < self.extreme_price:
                self.extreme_price = price
                self.total_trend = self.start_price - self.extreme_price
                messages = [
                    f"💀 Giá XAU: {price:.0f}, giảm {abs(delta):.0f}$, ĐÁY MỚI → Tổng giảm: {self.total_trend:.0f}$"]
            else:
                pull_amt = price - self.extreme_price
                pull_pct = (pull_amt / (self.start_price - self.extreme_price)) * 100

                if pull_pct >= 100:
                    self.trend = "up"
                    self.start_price = self.extreme_price
                    self.extreme_price = price
                    self.total_trend = self.extreme_price - self.start_price
                    messages = [f"🤩 Giá XAU: {price:.0f}, ĐẢO CHIỀU AN TOÀN → Tổng tăng: {self.total_trend:.0f}$"]
                elif pull_pct >= 40:
                    self.pre_reset_trend = "down"
                    self.trend = None
                    self.reset_price = price
                    old_total = self.total_trend
                    self.total_trend = 0
                    messages = [
                        f"🤩 Giá XAU: {price:.0f}, tăng {pull_amt:.0f}$, Pullback {pull_pct:.0f}% AN TOÀN (Tổng giảm cũ: {old_total:.0f}$)"]
                else:
                    messages = [
                        f"📈 Giá XAU: {price:.0f}, tăng {pull_amt:.0f}$, Pullback {pull_pct:.0f}% → Tổng giảm: {self.total_trend:.0f}$"]

        self.last_price = price
        return "\n".join(messages)