from flask import Flask
import threading
import bot  # Import your bot script

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Flask!'

def run_flask():
    app.run()

def run_bot():
    bot.run_bot()

if __name__ == "__main__":
    # Run Flask in one thread and bot in another
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_bot)

    flask_thread.start()
    bot_thread.start()