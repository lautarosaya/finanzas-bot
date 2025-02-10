import psycopg2
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

# 🔐 Cargar credenciales desde variables de entorno (IMPORTANTE para seguridad)
DB_HOST = os.getenv("DB_HOST", "tu_host_aqui")
DB_NAME = os.getenv("DB_NAME", "tu_db_aqui")
DB_USER = os.getenv("DB_USER", "tu_usuario_aqui")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tu_password_aqui")
DB_PORT = os.getenv("DB_PORT", "5432")  # PostgreSQL usa 5432 por defecto
BOT_TOKEN = os.getenv("BOT_TOKEN", "tu_token_de_telegram")


# 📌 Función para conectar a PostgreSQL
def conectar_db():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )


# 📌 Crear tablas si no existen
def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS finanzas (
            id SERIAL PRIMARY KEY,
            usuario_id BIGINT UNIQUE,
            sueldo NUMERIC DEFAULT 0
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            usuario_id BIGINT,
            descripcion TEXT NOT NULL,
            monto NUMERIC NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES finanzas (usuario_id) ON DELETE CASCADE
        )
    """
    )

    conn.commit()
    conn.close()


# 📌 Comando /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "¡Hola! Soy tu bot financiero 💰\n"
        "Usa /sueldo <monto> para registrar tu sueldo.\n"
        "Usa /gasto <descripcion> <monto> para agregar un gasto.\n"
        "Usa /resumen para ver el estado de tus finanzas."
    )


# 📌 Comando /sueldo
async def sueldo(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        await update.message.reply_text("Uso correcto: /sueldo <monto>")
        return

    try:
        monto = float(context.args[0])
        usuario_id = update.message.chat_id

        conn = conectar_db()
        cursor = conn.cursor()

        # Insertar o actualizar sueldo del usuario
        cursor.execute(
            "INSERT INTO finanzas (usuario_id, sueldo) VALUES (%s, %s) ON CONFLICT (usuario_id) DO UPDATE SET sueldo = EXCLUDED.sueldo",
            (usuario_id, monto),
        )

        conn.commit()
        conn.close()

        await update.message.reply_text(f"Sueldo registrado: ${monto}")

    except ValueError:
        await update.message.reply_text("Por favor, ingresa un monto válido.")


# 📌 Comando /gasto
async def gasto(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        await update.message.reply_text("Uso correcto: /gasto <descripcion> <monto>")
        return

    try:
        descripcion = " ".join(context.args[:-1])
        monto = float(context.args[-1])
        usuario_id = update.message.chat_id

        conn = conectar_db()
        cursor = conn.cursor()

        # Insertar el gasto
        cursor.execute(
            "INSERT INTO gastos (usuario_id, descripcion, monto) VALUES (%s, %s, %s)",
            (usuario_id, descripcion, monto),
        )

        conn.commit()
        conn.close()

        await update.message.reply_text(f"Gasto registrado: {descripcion} - ${monto}")

    except ValueError:
        await update.message.reply_text("Por favor, ingresa un monto válido.")


# 📌 Comando /resumen
async def resumen(update: Update, context: CallbackContext):
    usuario_id = update.message.chat_id

    conn = conectar_db()
    cursor = conn.cursor()

    # Obtener sueldo
    cursor.execute("SELECT sueldo FROM finanzas WHERE usuario_id = %s", (usuario_id,))
    sueldo = cursor.fetchone()
    sueldo = sueldo[0] if sueldo else 0

    # Obtener total de gastos
    cursor.execute("SELECT SUM(monto) FROM gastos WHERE usuario_id = %s", (usuario_id,))
    total_gastos = cursor.fetchone()[0]
    total_gastos = total_gastos if total_gastos else 0

    # Obtener gastos detallados
    cursor.execute(
        "SELECT descripcion, monto FROM gastos WHERE usuario_id = %s", (usuario_id,)
    )
    gastos = cursor.fetchall()

    conn.close()

    mensaje = f"💰 **Resumen Financiero** 💰\n\n"
    mensaje += f"📌 **Sueldo:** ${sueldo}\n"
    mensaje += f"📉 **Total Gastos:** ${total_gastos}\n"
    mensaje += f"📈 **Saldo Disponible:** ${sueldo - total_gastos}\n\n"

    if gastos:
        mensaje += "📊 **Detalle de Gastos:**\n"
        for descripcion, monto in gastos:
            mensaje += f"  - {descripcion}: ${monto}\n"

    await update.message.reply_text(mensaje)


# 📌 Configurar el bot
def main():
    inicializar_db()  # Crear tablas al iniciar

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sueldo", sueldo))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("resumen", resumen))

    print("🤖 Bot en ejecución...")
    app.run_polling()


if __name__ == "__main__":
    main()
