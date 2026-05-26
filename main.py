import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Import the processing utility functions we just made
from watermark_utils import apply_text_watermark, apply_logo_watermark

# --- Web Server for Render Health Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Watermark Bot is active!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

# --- Conversation States ---
# Unique integers identifying different parts of the dialogue
PHOTO, CHOOSE_TYPE, TEXT_INPUT, LOGO_INPUT = range(4)

# Define choice keyboard
choice_keyboard = [["Text Watermark ✍️", "Logo Watermark 🖼️"]]
markup = ReplyKeyboardMarkup(choice_keyboard, one_time_keyboard=True, resize_keyboard=True)


# --- Bot Flow Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Image Watermark Tool Bot! 🛡️\n\n"
        "This bot helps you protect your images from unauthorized copying.\n\n"
        "**To begin, please send me the MAIN PHOTO you want to watermark.**",
        parse_mode="Markdown"
    )
    return PHOTO

async def handle_main_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the main photo and asks for the watermark type."""
    # Store the photo file_id to use later
    context.user_data['main_photo_id'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        "Photo received successfully!\n\n"
        "How do you want to protect it? Choose an option from the keyboard:",
        reply_markup=markup
    )
    return CHOOSE_TYPE

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Branches the conversation based on user's choice."""
    user_choice = update.message.text
    
    if user_choice == "Text Watermark ✍️":
        await update.message.reply_text(
            "Enter the text you want to use as a watermark (e.g., '© YOUR NAME' or your website):",
            reply_markup=ReplyKeyboardRemove()
        )
        return TEXT_INPUT
    
    elif user_choice == "Logo Watermark 🖼️":
        await update.message.reply_text(
            "Please upload your LOGO IMAGE file (JPG or PNG with transparency) that you want overlayed:",
            reply_markup=ReplyKeyboardRemove()
        )
        return LOGO_INPUT
    
    else:
        await update.message.reply_text("Invalid selection. Please use the keyboard options.", reply_markup=markup)
        return CHOOSE_TYPE

async def handle_text_watermarking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Applies Text watermark and returns the final image."""
    watermark_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")

    main_photo_id = context.user_data.get('main_photo_id')
    
    # Define temporary file paths
    base_file = f"base_{update.message.message_id}.jpg"
    final_file = f"final_txt_{update.message.message_id}.jpg"

    try:
        # 1. Download main image
        file = await context.bot.get_file(main_photo_id)
        await file.download_to_drive(base_file)

        # 2. Call PIL utility function
        success, error_msg = apply_text_watermark(base_file, final_file, text=watermark_text)

        if success:
            # 3. Send final image back
            with open(final_file, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"✅ Protected image with text: `{watermark_text}`",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(f"Processing error: {error_msg}")
            
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Failed to process your image.")
    finally:
        # Cleanup temporary local files on Render
        for f in (base_file, final_file):
            if os.path.exists(f):
                os.remove(f)

    return ConversationHandler.END  # End this specific convo flow

async def handle_logo_watermarking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Applies Logo overlay and returns the final image."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")

    main_photo_id = context.user_data.get('main_photo_id')
    logo_file_id = update.message.photo[-1].file_id

    # Define temporary file paths
    base_file = f"base_{update.message.message_id}.jpg"
    logo_file = f"logo_{update.message.message_id}.png"
    final_file = f"final_logo_{update.message.message_id}.jpg"

    try:
        # 1. Download main and logo images
        file_base = await context.bot.get_file(main_photo_id)
        await file_base.download_to_drive(base_file)
        
        file_logo = await context.bot.get_file(logo_file_id)
        await file_logo.download_to_drive(logo_file)

        # 2. Call PIL utility function
        success, error_msg = apply_logo_watermark(base_file, logo_file, final_file)

        if success:
            # 3. Send final image back
            with open(final_file, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption="✅ Protected image with your logo overlay!")
        else:
            await update.message.reply_text(f"Logo Processing error: {error_msg}")
            
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Failed to overlay your logo.")
    finally:
        # Cleanup temporary local files on Render
        for f in (base_file, logo_file, final_file):
            if os.path.exists(f):
                os.remove(f)

    return ConversationHandler.END  # End this flow

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# --- Main Main Async Application Lifecycle ---

async def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Missing TELEGRAM_TOKEN environment variable.")

    # Start dummy health server for Render loop
    threading.Thread(target=run_health_server, daemon=True).start()

    # Build the application
    app = Application.builder().token(TOKEN).build()
    
    # -------------------------------------------------------------
    # Define the ConversationFlow Handler
    # This manages the states (waiting for photo -> choice -> result)
    # -------------------------------------------------------------
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.PHOTO, start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_main_photo)],
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
            TEXT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_watermarking)],
            LOGO_INPUT: [MessageHandler(filters.PHOTO, handle_logo_watermarking)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Register conversation handler
    app.add_handler(conv_handler)
    
    # Ensure startup sequence runs before polling starts
    print("Image Watermark Engine is initializing...")
    
    async with app:
        await app.initialize()
        await app.start()
        print("Bot is now polling...")
        await app.updater.start_polling()
        # Keep alive loop
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
