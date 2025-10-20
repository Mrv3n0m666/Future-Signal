
# Future-Signal

Golden Moment signal bot for Binance Futures (USDT-M).
- Multi-timeframe: 1m, 3m, 5m
- Indicators: EMA(7,25,99), RSI(6,24), Volume spike, ATR for TP/SL
- Dynamic coin list: top-volume + new-listing
- Auto TP/SL tracking and stats (daily/monthly)
- Sends signals & updates to Telegram

## Setup
1. Fill .env with TELEGRAM_TOKEN and TELEGRAM_CHAT_ID (or use Railway variables)
2. Install dependencies: pip install -r requirements.txt
3. Run: python main.py
