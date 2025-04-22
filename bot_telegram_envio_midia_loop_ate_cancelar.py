
import sqlite3
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "7501667861:AAH0FkXxdW5GtbZW0I5phVUdMshh6WRM-80"
DB_PATH = "bot_canais.db"

def criar_tabelas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS canais (id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY)")
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

def adicionar_canal(canal_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO canais (id) VALUES (?)", (canal_id,))
    conn.commit()
    conn.close()

def remover_canal(canal_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM canais WHERE id = ?", (canal_id,))
    conn.commit()
    conn.close()

def listar_canais():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM canais")
    canais = [x[0] for x in c.fetchall()]
    conn.close()
    return canais

def adicionar_admin(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins VALUES (?)", (username,))
    conn.commit()
    conn.close()

def is_admin(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM admins WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

def is_autorizado(username):
    if is_admin(username):
        return True
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM usuarios WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result is not None

# === Estados ===
user_states = {}
media_cache = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not is_autorizado(username):
        await update.message.reply_text("❌ Sem permissão.")
        return

    keyboard = [
        [InlineKeyboardButton("📤 Enviar mensagem", callback_data="start_envio")],
        [InlineKeyboardButton("❌ Cancelar envio", callback_data="cancelar_envio")],
        [InlineKeyboardButton("➕ Adicionar canal", callback_data="add_canal")],
        [InlineKeyboardButton("➖ Remover canal", callback_data="rem_canal")],
        [InlineKeyboardButton("📋 Listar canais", callback_data="listar_canais")]
    ]
    await update.message.reply_text("📨 Painel de Controle", reply_markup=InlineKeyboardMarkup(keyboard))

async def botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    username = update.effective_user.username
    await query.answer()

    if not is_autorizado(username):
        await query.edit_message_text("❌ Sem permissão.")
        return

    data = query.data
    user_states[username] = data
    media_cache[username] = []

    if data == "start_envio":
        await query.edit_message_text("📤 Envie até 10 imagens com legenda para formar um álbum ou envie texto.")
    elif data == "cancelar_envio":
        user_states.pop(username, None)
        media_cache.pop(username, None)
        await query.edit_message_text("❌ Envio cancelado.")
    elif data == "add_canal":
        await query.edit_message_text("📥 Envie o ID do canal para adicionar.")
    elif data == "rem_canal":
        await query.edit_message_text("🗑️ Envie o ID do canal para remover.")
    elif data == "listar_canais":
        canais = listar_canais()
        texto = "\n".join(str(c) for c in canais) if canais else "📭 Nenhum canal registrado."
        await query.edit_message_text(f"📋 *Canais cadastrados:*\n{texto}", parse_mode="Markdown")

async def receber_midia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    estado = user_states.get(username)

    if not estado or not is_autorizado(username):
        return

    canais = listar_canais()
    if not canais:
        await update.message.reply_text("⚠️ Nenhum canal cadastrado.")
        return

    if estado == "start_envio":
        if update.message.video:
            for canal in canais:
                await context.bot.send_video(chat_id=canal, video=update.message.video.file_id, caption=update.message.caption or "", parse_mode="HTML")
            await update.message.reply_text("🎥 Vídeo enviado.")
        elif update.message.audio:
            for canal in canais:
                await context.bot.send_audio(chat_id=canal, audio=update.message.audio.file_id, caption=update.message.caption or "")
            await update.message.reply_text("🎵 Áudio enviado.")
        elif update.message.document:
            for canal in canais:
                await context.bot.send_document(chat_id=canal, document=update.message.document.file_id, caption=update.message.caption or "")
            await update.message.reply_text("📎 Documento enviado.")
        elif update.message.photo:
            media_cache[username].append(InputMediaPhoto(media=update.message.photo[-1].file_id, caption=update.message.caption or None))
            if len(media_cache[username]) >= 10:
                for canal in canais:
                    await context.bot.send_media_group(chat_id=canal, media=media_cache[username])
                await update.message.reply_text("✅ Álbum enviado.")
                media_cache[username] = []
        elif update.message.text:
            for canal in canais:
                await context.bot.send_message(chat_id=canal, text=update.message.text, parse_mode="HTML")
            await update.message.reply_text("✅ Mensagem enviada.")
        return

    if estado == "add_canal":
        try:
            adicionar_canal(int(update.message.text))
            await update.message.reply_text("✅ Canal adicionado.")
        except:
            await update.message.reply_text("❌ ID inválido.")
    elif estado == "rem_canal":
        try:
            remover_canal(int(update.message.text))
            await update.message.reply_text("🗑️ Canal removido.")
        except:
            await update.message.reply_text("❌ ID inválido.")

    user_states.pop(username, None)

async def main():
    criar_tabelas()
    adicionar_admin("quizorddvip")  # admin padrão
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botao))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL, receber_midia))
    print("✅ Bot de álbum rodando...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
import asyncio
nest_asyncio.apply()
asyncio.get_event_loop().run_until_complete(main())


# Cancelar envio
async def cancelar_envio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["modo_envio"] = False
    await update.message.reply_text("❌ Modo envio cancelado.")

app.add_handler(CommandHandler("cancelar", cancelar_envio))
