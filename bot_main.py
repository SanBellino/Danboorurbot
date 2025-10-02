# --- PACKAGE IMPORTS ---
import os             #For environment variables (such as the TOKEN one for the bot)
import logging        #For logging errors and info to the console
import requests       #For making HTTP requests to Danbooru API
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton 
# 'Update' = incoming update from Telegram (messages, callbacks, etc.)
# 'InlineKeyboardMarkup' and 'InlineKeyboardButton' = to create inline buttons under messages

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
# 'ApplicationBuilder' = to build the bot application
# 'ContextTypes' = provides context info for the handlers (like args passed to commands)
# 'CommandHandler' = to handle commands like /start, /character, etc.
# 'CallbackQueryHandler' = to handle button presses

#Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Load environment variables from .env file
TOKEN = os.getenv("TOKEN")


# --- UTILS ---
"""
 This function prevents Telegram errors caused by captions being too long.
- Splits Danbooru's 'tag_string' into a list of tags.
- Iterates over tags, adding them until one of two limits is reached:
  1. max_tags = number of tags limit
  2. max_length = character count limit
- Returns a string with allowed tags joined by spaces.
"""
def get_limited_tags(post, max_tags=15, max_length=900):
    all_tags = post.get("tag_string", "").split()  #Extract tags as a list
    limited_tags = []                              #Final tag list to return
    current_length = 0

    for tag in all_tags:
        # Stop if the maximum number of tags is reached
        if len(limited_tags) >= max_tags:
            break
        # Stop if adding this tag would exceed the character limit
        if current_length + len(tag) + 1 > max_length:
            break
        limited_tags.append(tag)
        current_length += len(tag) + 1  # +1 for the space

    return " ".join(limited_tags)


"""   Fetch a random image from Danbooru for the given character.
    - Builds the API request to Danbooru (rating:safe, random result).
    - Validates image size/availability.
    - Sends the image with a caption of limited tags.
    - Adds an inline button: "Another one" → fetches another random image."""
async def send_character_image(message, character: str):
    url = f"https://danbooru.donmai.us/posts.json?tags={character}+rating:safe&limit=1&random=true"
    headers = {"User-Agent": os.getenv("USER_AGENT")} # Set a custom User-Agent for Danbooru API requests, to avoid being blocked

    try:
        #Make the request to Danbooru
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()

        if not data:
            await message.reply_text("No image found for that character.")
            return
        
        # Extract post info (only first result, because limit=1)
        post = data[0]
        # Get best available image URL (prefer full file_url, then fallback)
        image_url = post.get("file_url") or post.get("large_file_url") or post.get("preview_file_url")
        photo_tags = get_limited_tags(post)

        # Skip if image is too large for Telegram (20MB limit)
        if post.get("file_size", 0) > 20_000_000:
            await message.reply_text(
                "Image is too large to send via Telegram.\n"
                f"Image URL: {image_url}"
            )
            return
        
        # Skip if no valid image URL
        if not image_url:
            await message.reply_text("Image URL invalid or unavailable.")
            return

        # Inline button
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔄 Another one", callback_data=f"another|{character}")]]
        )
        
        # Send the photo with tags + button
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

"""
    Handler for /character command.
    - Reads the character name from user arguments.
    - Converts spaces into underscores (as Danbooru uses underscores).
    - Calls send_character_image() to fetch and send result.
"""
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
    """
    Main entry point of the bot.
    - Builds the Telegram app.
    - Registers command and button handlers.
    - Starts polling (listening for updates from Telegram).
    """
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("character", character))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("tags", tags))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
