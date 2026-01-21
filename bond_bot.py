import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === ТВОЙ ЧЕК-ЛИСТ (логика) ===
def check_bond(fin_data):
    # fin_data = {
    #   'name': 'Роснефть',
    #   'years': [2023, 2022, 2021],
    #   'net_profit': [200, 180, 160],      # млрд руб
    #   'interest_expense': [30, 28, 25],
    #   'operating_cf': [250, 230, 210],
    #   'revenue': [9000, 8500, 8000],
    #   'total_debt': 1200
    # }
    p = fin_data['net_profit']
    i = fin_data['interest_expense'][-1]  # последний год
    cf = fin_data['operating_cf']
    debt = fin_data['total_debt']
    rev = fin_data['revenue']

    checks = [False]*5
    reasons = [""]*5

    # 1. Стабильная прибыль
    if all(x > 0 for x in p[-3:]):
        checks[0] = True
    else:
        reasons[0] = "Убытки или нестабильная прибыль"

    # 2. Проценты ≤40% прибыли
    profit_last = p[-1]
    if profit_last > 0 and i / profit_last <= 0.4:
        checks[1] = True
    else:
        reasons[1] = f"Проценты = {i/profit_last:.1%} прибыли (>40%)"

    # 3. Операционный ДП > 0
    if all(x > 0 for x in cf[-3:]):
        checks[2] = True
    else:
        reasons[2] = "Операционный денежный поток ≤0"

    # 4. Долг ≤ 4× прибыль
    if profit_last > 0 and debt / profit_last <= 4:
        checks[3] = True
    else:
        reasons[3] = f"Долг = {debt / profit_last:.1f}× годовой прибыли (>4×)"

    # 5. Выручка не падает 2+ года
    if not (rev[-1] < rev[-2] < rev[-3]):
        checks[5-1] = True
    else:
        reasons[4] = "Выручка падает 2+ года подряд"

    return checks, reasons

# === БАЗА ДАННЫХ (временно) ===
BOND_DB = {
    "RU000A0JW5G5": {
        "name": "ПАО «Роснефть»",
        "isin": "RU000A0JW5G5",
        "fin_data": {
            "years": [2023, 2022, 2021],
            "net_profit": [200, 180, 160],
            "interest_expense": [30, 28, 25],
            "operating_cf": [250, 230, 210],
            "revenue": [9000, 8500, 8000],
            "total_debt": 700  # млрд руб
        }
    },
    "RU000A0JSF87": {
        "name": "ПАО «Газпром»",
        "isin": "RU000A0JSF87",
        "fin_data": {
            "years": [2023, 2022, 2021],
            "net_profit": [80, -100, 200],  # убыток в 2022!
            "interest_expense": [40, 38, 35],
            "operating_cf": [1200, 900, 1100],
            "revenue": [8000, 7500, 8200],
            "total_debt": 500
        }
    }
}

# === TELEGRAM БОТ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришлите ISIN облигации (например, RU000A0JW5G5).")

async def handle_isin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isin = update.message.text.strip().upper()
    if isin not in BOND_DB:
        await update.message.reply_text(f"❌ ISIN {isin} не найден в базе. Пока поддерживаются только:\n• RU000A0JW5G5 (Роснефть)\n• RU000A0JSF87 (Газпром)")
        return

    bond = BOND_DB[isin]
    name = bond["name"]
    fin = bond["fin_data"]

    checks, reasons = check_bond(fin)

    response = f"🔍 Анализ облигации\nISIN: {isin}\nЭмитент: {name}\n\n"
    for i, (ok, reason) in enumerate(zip(checks, reasons), 1):
        mark = "✅" if ok else "❌"
        response += f"{mark} Пункт {i}: {'OK' if ok else reason}\n"

    if all(checks):
        response += "\n🟢 ВЕРДИКТ: Подходит по всем пунктам!"
    else:
        response += "\n🔴 ВЕРДИКТ: Не проходит чек-лист."

    await update.message.reply_text(response)

# === ЗАПУСК ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Замени 'YOUR_BOT_TOKEN' на токен от @BotFather
    import os
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_isin))
    print("Бот запущен...")
    app.run_polling()