#Package import
import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler


#Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# The bot token is stored in an .env file, os.getenv fetches it
TOKEN = os.getenv("TOKEN")


# --- COMMAND HANDLERS ---

# The start commands sends an introductory message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "This (pretty basic) bot fetches a random image from Danbooru based on the character name you provide.\n"
        "I've fiddled with it and despite the bot only sends pics that are rated as 'safe', some images might be borderline.\n"
        "Use at your own risk.\n\n" \
        "type /help for a list of commands"
    )

# The help command lists available commands
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/character <name> → random image of a character \n"
        "/tags will give the link to Danbooru tags page"
    )

# The tags command gives a link to Danbooru tags page
async def tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "https://danbooru.donmai.us/wiki_pages/tag_groups"
    )

# The character command fetches a random image of the selected character from Danbooru
async def character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("You didn't write the name of any character after /character!")
        return
    #Join args with underscores (example: if you type "Yuuki Asuna" it will become "Yuuki_Asuna"), since Danbooru tags use underscores
    character = "_".join(context.args)

    # API endpoint: Searches by character name, allows only safe rated posts and sends only 1 image, chosen randomly. This API doesn't need a key.
    url = f"https://danbooru.donmai.us/posts.json?tags={character}+rating:safe&limit=1&random=true"

    headers = {
        "User-Agent": os.getenv("USER_AGENT")
    }
    await update.message.reply_text("Fetching image...")

    try:
        # Make the request to Danbooru API
        response = requests.get(url)
        data = response.json()
        
        #If no image is found, the bot will send a message to the user.
        if not data:
            await update.message.reply_text("No image found for that character. If you typed for example 'Asuna Yuuki, try 'Yuuki Asuna' instead.")
            return
        
        # If an image is found, the bot will send it to the user.
        # data is the json that Danbooru gives us, it's a list of every post, by setting it to "0" we take the first post that it gives us, it's always random because danbooru gives the posts in a random order. 
        # file_url is a key in that json, which stores the url (value) of our image, we store it inside image_url.
        # tag_string is another key in that json, which stores the tags of our image, we store it inside photo_tags.
        post = data[0]
        image_url = data[0].get("file_url")
        photo_tags = post.get("tag_string", "") 

        #If no url is found, the bot will send a message to the user.
        if not image_url:
            await update.message.reply_text("Post found, but no image URL available.")
            return

        #Send the image with tags as caption
        await update.message.reply_photo(photo=image_url, caption=f"Tags:\n{photo_tags}")

    except Exception as e:
        await update.message.reply_text("Error fetching image.")
        logging.error(e)




# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("character", character))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("tags", tags))

    # Run the bot in polling mode (keeps it active and listening for commands)
    app.run_polling()

# Run the bot when the script is executed directly
if __name__ == "__main__":
    main()
