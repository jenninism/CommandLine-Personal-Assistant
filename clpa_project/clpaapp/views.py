import wikipedia
import string
import datetime
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

note_pending_sessions = {}  #NOTES

# Temporary store for tracking pending weather location requests
weather_pending_sessions = {}

# Replace this with your OpenWeatherMap API key
WEATHER_API_KEY = 'your_openweathermap_api_key'


def chat_page(request):
    return render(request, 'clpaapp/chat.html')

@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        message = message.translate(str.maketrans('', '', string.punctuation)).strip()

        timer_match = re.search(r"set timer for (\d+)\s*(seconds?|minutes?|hours?)", message)
        if timer_match:
            amount = int(timer_match.group(1))
            unit = timer_match.group(2)
            return JsonResponse({'response': f"⏱ Timer set for {amount} {unit}!"})

        if any(phrase in message for phrase in ["timer", "i need timer", "please timer"]):
            return JsonResponse({'response': "How long should I set the timer for? (e.g., 'set timer for 5 minutes')"})
        session_id = request.session.session_key or "default"

        # Check if user is replying with a location for weather
        if weather_pending_sessions.get(session_id):
            weather_pending_sessions[session_id] = False
            weather_info = get_weather(message)
            return JsonResponse({'response': weather_info})
        
        if session_id in note_pending_sessions:
                note_state = note_pending_sessions[session_id]
                if note_state["step"] == "title":
                    note_state["title"] = message
                    note_state["step"] = "content"
                    return JsonResponse({'response': "Great! What should the note say?"})
                elif note_state["step"] == "content":
                    title = note_state["title"]
                    content = message

                    filename = f"{title.replace(' ', '_')}.txt"
                    filepath = os.path.join("notes", filename)
                    os.makedirs("notes", exist_ok=True)

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

                    del note_pending_sessions[session_id]

                    try:
                        os.system(f"notepad.exe {filepath}")  # For Windows; change if needed
                    except Exception:
                        pass

                    return JsonResponse({'response': f"Note '{title}' saved and opened in Notepad!"})

            # Trigger note-taking on 'new note' command
        message_lower = message.lower().translate(str.maketrans('', '', string.punctuation)).strip()
        if message_lower == "new note":
            note_pending_sessions[session_id] = {"step": "title", "title": ""}
            return JsonResponse({'response': "Sure! What should the title of the note be?"})

        replies = {
            "hi": "Hello!",
            "hello": "Hi there!",
            "how are you": "I'm just code, but thanks for asking!",
            "what can you do": "I can answer questions, give daily advice, and open websites.",
            "who are you": "I am your Command Line Personal Assistant.",
            "what is your name": "You can call me CLPA!",
            "bye": "Goodbye!",
            "thank you": "You're welcome!",
            "what time is it": "I'm not wearing a watch, but your taskbar might help.",
            "what is programming language": "Programming languages are tools for writing instructions to computers.",
            "what is pip": "Pip is a package manager for Python packages.",
            "what is python": "Python is a popular programming language that's beginner-friendly.",
            "what is django": "Django is a high-level Python web framework for building websites.",
            "do you love me": "01011001 01000101 01010011 ❤️",
            "help": None  # special case
        }

        websites = {
            "open google": "https://www.google.com",
            "open youtube": "https://www.youtube.com",
            "open facebook": "https://www.facebook.com",
            "open twitter": "https://www.twitter.com",
            "open gmail": "https://mail.google.com",
            "open github": "https://github.com",
        }

        url = None
        response = None

        if message == "clear":
            response = "[CLEAR_SCREEN]"
        elif message == "exit":
            response = "Goodbye! Closing the session..."
        elif message == "time":
            now = datetime.datetime.now()
            response = "Current time is " + now.strftime("%H:%M:%S")
        elif message == "date":
            today = datetime.date.today()
            response = "Today's date is " + today.strftime("%B %d, %Y")
        elif message == "help":
            response = "You can ask me:\n- " + "\n- ".join(
                sorted(list(replies.keys()) + list(websites.keys()) + ["clear", "exit", "time", "date"])
            )
        elif message in websites:
            url = websites[message]
            response = f"Opening {message.split()[-1].capitalize()}..."
        elif any(message.startswith(q) for q in ["who is", "what is", "where is", "who was", "what are", "who are"]):
            try:
                summary = wikipedia.summary(message, sentences=2)
                response = summary
            except wikipedia.DisambiguationError as e:
                response = f"That’s too broad. Did you mean: {', '.join(e.options[:5])}?"
            except wikipedia.PageError:
                response = "Sorry, I couldn't find anything about that."
            except Exception:
                response = "There was a problem fetching the info."
      

        

        
        else:
            response = replies.get(message, "Sorry, I don't understand that yet.")

        return JsonResponse({'response': response, 'url': url})

    return JsonResponse({'error': 'Invalid method'}, status=400)
