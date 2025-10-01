#Package import
import os
import logging
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler


#Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# The bot token is stored in an .env file, os.getenv fetches it
TOKEN = os.getenv("TOKEN")


# --- UTILS ---
"""
      Limit the number of tags to avoid 'Message caption is too long' error.
    Returns a string with at most 'max_tags' tags,
    or until the combined length reaches 'max_length' characters.
"""
def get_limited_tags(post, max_tags=15, max_length=900):
    all_tags = post.get("tag_string", "").split()
    limited_tags = []
    current_length = 0

    for tag in all_tags:
        # Se supero il numero massimo di tag → stop
        if len(limited_tags) >= max_tags:
            break
        # Se supero la lunghezza massima → stop
        if current_length + len(tag) + 1 > max_length:
            break
        limited_tags.append(tag)
        current_length += len(tag) + 1  # +1 per lo spazio

    return " ".join(limited_tags)

async def send_character_image(message, character: str):
    """Fetch a random image from Danbooru and send it with limited tags + button"""
    url = f"https://danbooru.donmai.us/posts.json?tags={character}+rating:safe&limit=1&random=true"
    headers = {"User-Agent": os.getenv("USER_AGENT")}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()

        if not data:
            await message.reply_text("No image found for that character.")
            return

        post = data[0]
        image_url = post.get("file_url") or post.get("large_file_url") or post.get("preview_file_url")
        photo_tags = get_limited_tags(post)

        if post.get("file_size", 0) > 20_000_000:
            await message.reply_text(
                "Image is too large to send via Telegram.\n"
                f"Image URL: {image_url}"
            )
            return

        if not image_url:
            await message.reply_text("Image URL invalid or unavailable.")
            return

        # Inline button
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔄 Another one", callback_data=f"another|{character}")]]
        )

        await message.reply_photo(photo=image_url, caption=f"Tags:\n{photo_tags}", reply_markup=keyboard)

    except Exception as e:
        await message.reply_text("Error fetching image.")
        logging.error(e)


# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "This (pretty basic) bot fetches a random image from Danbooru based on the character name you provide.\n"
        "I've fiddled with it and despite the bot only sends pics that are rated as 'safe', some images might be borderline.\n"
        "Use at your own risk.\n\n"
        "type /help for a list of commands"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/character <name> → random image of a character \n"
        "/tags → link to Danbooru tags page"
    )

async def tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "https://danbooru.donmai.us/wiki_pages/tag_groups"
    )

# The character command fetches a random image of the selected character from Danbooru
async def character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("You didn't write the name of any character after /character!")
        return

    character = "_".join(context.args)
    await update.message.reply_text("Fetching image...")
    await send_character_image(update.message, character)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("another|"):
        character = query.data.split("|", 1)[1]
        await send_character_image(query.message, character)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("character", character))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("tags", tags))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
