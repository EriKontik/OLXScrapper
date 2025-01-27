import telebot
import threading
import json
from main import load_dictionary  # Assuming you have a `load_dictionary` function in `main.py`

# Your Telegram bot token
BOT_TOKEN = "7670200451:AAGTPRT7iCgiMDL7nZYYI3uWTCtmlVX5PIg"
bot = telebot.TeleBot(BOT_TOKEN)

# Path to store chat IDs
CHAT_ID_FILE = "chat_ids.json"

# Load existing chat IDs from the file (if any)
def load_chat_ids():
    try:
        with open(CHAT_ID_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save chat IDs to the file
def save_chat_ids(chat_ids):
    with open(CHAT_ID_FILE, "w") as f:
        json.dump(chat_ids, f)

# Start command to activate the bot for a user
@bot.message_handler(commands=["start"])
def start_bot(message):
    chat_id = message.chat.id
    active_users = load_chat_ids()  # Load current chat_ids from file
    if chat_id not in active_users:
        active_users[chat_id] = True  # Add the new user to active users
        save_chat_ids(active_users)  # Save updated chat_ids to file
        bot.send_message(chat_id, "Bot activated! You'll now receive updates.")
    else:
        bot.send_message(chat_id, "You're already subscribed to updates.")

# Function to send updates to all active users
def send_updates(products_data):
    active_users = load_chat_ids()  # Load current chat_ids from file

    def send_message(chat_id, product_data):
        try:
            message = (
                f"📦 New Product Found!\n\n"
                f"🛒 *Name*: {product_data['name']}\n"
                f"💰 *Price*: {product_data['price']} UAH\n"
                f"🔗 *Link*: [View Product]({product_data['link']})\n"
                f"📅 *Date*: {product_data['date']}"
            )
            bot.send_message(chat_id, message, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")

    threads = []
    for chat_id in active_users.keys():
        for product_data in products_data:
            thread = threading.Thread(target=send_message, args=(chat_id, product_data))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

# Example product data for testing
def main_tg(product_category):
    try:
        data_to_send = load_dictionary(f"data_to_send_{product_category}.pkl").values()
        if data_to_send:
            send_updates(data_to_send)
        else:
            print("No data to send.")
    except FileNotFoundError:
        print(f"Data file for category '{product_category}' not found.")
    except Exception as e:
        print(f"Error loading data: {e}")

def startup_tg(product_category):
    threading.Thread(target=main_tg, args=(product_category,)).start()

# Start polling to keep the bot alive
if __name__ == "__main__":
    # Run main_tg in the background to load product data, but don't send updates until users are ready
    threading.Thread(target=main_tg, args=("iPhone7",)).start()

    # Keep polling the bot to handle incoming commands
    bot.polling(none_stop=True)