

FAQ_RESPONSES = {
    "hi": "Hello!",
    "hello": "Hi there!",
    "what can you do": "I can answer FAQ questions.",
    "who are you": "I am your Command Line Personal Assistant.",
    "bye": "Goodbye!",
    "how are you": "I'm just code, but thanks for asking!"
}

def get_bot_response(message):
    message = message.lower().strip()
    return FAQ_RESPONSES.get(message, "I'm sorry, I didn't understand that command.")

