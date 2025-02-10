from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
import os
import psycopg2
from psycopg2 import sql

# ✅ Cargar variables de entorno
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")


# ✅ Conectar a PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )


# ✅ Crear tabla si no existe
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS finanzas (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE,
            sueldo DECIMAL(10,2),
            ahorro DECIMAL(10,2)
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            descripcion TEXT,
            monto DECIMAL(10,2),
            FOREIGN KEY (user_id) REFERENCES finanzas(user_id) ON DELETE CASCADE
        )
    """
    )
    conn.commit()
    cur.close()
    conn.close()


# ✅ Comando /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "¡Hola! Soy tu bot financiero. Usa /sueldo, /gasto y /resumen para administrar tu dinero."
    )


# ✅ Comando /sueldo
async def set_sueldo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /sueldo <monto> <% ahorro>")
        return

    sueldo = float(context.args[0])
    ahorro = sueldo * (float(context.args[1]) / 100)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO finanzas (user_id, sueldo, ahorro) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET sueldo = EXCLUDED.sueldo, ahorro = EXCLUDED.ahorro
    """,
        (user_id, sueldo, ahorro),
    )
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(
        f"💰 Sueldo registrado: ${sueldo:.2f}\n💾 Ahorro estimado: ${ahorro:.2f}"
    )


# ✅ Comando /gasto
async def add_gasto(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /gasto <descripción> <monto>")
        return

    descripcion = context.args[0]
    monto = float(context.args[1])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gastos (user_id, descripcion, monto) VALUES (%s, %s, %s)",
        (user_id, descripcion, monto),
    )
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(f"📌 Gasto añadido: {descripcion} - ${monto:.2f}")


# ✅ Comando /resumen
async def resumen(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener sueldo y ahorro
    cur.execute("SELECT sueldo, ahorro FROM finanzas WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text(
            "⚠️ No tienes sueldo registrado. Usa /sueldo para agregarlo."
        )
        return

    sueldo, ahorro = row

    # Obtener gastos
    cur.execute("SELECT descripcion, monto FROM gastos WHERE user_id = %s", (user_id,))
    gastos = cur.fetchall()
    total_gastos = sum(monto for _, monto in gastos)

    conn.commit()
    cur.close()
    conn.close()

    # Construir mensaje
    mensaje = f"📊 *Resumen financiero*\n\n"
    mensaje += f"💰 *Sueldo:* ${sueldo:.2f}\n"
    mensaje += f"💾 *Ahorro estimado:* ${ahorro:.2f}\n"
    mensaje += f"💸 *Total Gastos:* ${total_gastos:.2f}\n"
    mensaje += f"📉 *Saldo Disponible:* ${sueldo - total_gastos - ahorro:.2f}\n\n"
    mensaje += "*📌 Detalle de gastos:*\n"
    for desc, monto in gastos:
        mensaje += f"  - {desc}: ${monto:.2f}\n"

    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ✅ Configurar el bot
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("sueldo", set_sueldo))
app.add_handler(CommandHandler("gasto", add_gasto))
app.add_handler(CommandHandler("resumen", resumen))


# ✅ Webhook en Render
async def set_webhook():
    await app.bot.set_webhook(WEBHOOK_URL)


app.run_webhook(listen="0.0.0.0", port=8080, webhook_url=WEBHOOK_URL)

# ✅ Crear tablas al iniciar
init_db()
