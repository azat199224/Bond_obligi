import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === ТВОЙ ЧЕК-ЛИСТ ===
def check_bond(fin_data):
    p = fin_data['net_profit']
    i = fin_data['interest_expense'][-1]
    cf = fin_data['operating_cf']
    debt = fin_data['total_debt']
    rev = fin_data['revenue']
    profit_last = p[-1]

    checks = [False] * 5
    reasons = [""] * 5

    if all(x > 0 for x in p[-3:]):
        checks[0] = True
    else:
        reasons[0] = "Убытки или нестабильная прибыль"

    if profit_last > 0 and i / profit_last <= 0.4:
        checks[1] = True
    else:
        reasons[1] = f"Проценты = {i / profit_last:.1%} прибыли (>40%)"

    if all(x > 0 for x in cf[-3:]):
        checks[2] = True
    else:
        reasons[2] = "Операционный денежный поток ≤0"

    if profit_last > 0 and debt / profit_last <= 4:
        checks[3] = True
    else:
        reasons[3] = f"Долг = {debt / profit_last:.1f}× годовой прибыли (>4×)"

    if not (rev[-1] < rev[-2] < rev[-3]):
        checks[4] = True
    else:
        reasons[4] = "Выручка падает 2+ года подряд"

    return checks, reasons

# === БАЗА ДАННЫХ ===
BOND_DB = {
    "RU000A0JW5G5": {
        "name": "ПАО «Роснефть»",
        "fin_data": {
            "net_profit": [200, 180, 160],
            "interest_expense": [30, 28, 25],
            "operating_cf": [250, 230, 210],
            "revenue": [9000, 8500, 8000],
            "total_debt": 700
        }
    }
}

# === TELEGRAM БОТ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришлите ISIN облигации.")

async def handle_isin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isin = update.message.text.strip().upper()
    if isin not in BOND_DB:
        await update.message.reply_text("ISIN не найден.")
        return
    bond = BOND_DB[isin]
    checks, reasons = check_bond(bond["fin_data"])
    response = f"Эмитент: {bond['name']}\n"
    for i, (ok, r) in enumerate(zip(checks, reasons), 1):
        response += f"{'✅' if ok else '❌'} Пункт {i}: {'OK' if ok else r}\n"
    response += "\n🟢 Подходит!" if all(checks) else "\n🔴 Не проходит."
    await update.message.reply_text(response)

# === ЗАПУСК ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_isin))
    app.run_polling()