import wikipedia
import string
import datetime
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess



note_pending_sessions = {}  #NOTES

# Temporary store for tracking pending weather location requests
weather_pending_sessions = {}

# Replace this with your OpenWeatherMap API key
WEATHER_API_KEY = 'your_openweathermap_api_key'


def chat_page(request):
    return render(request, 'clpaapp/chat.html')

def get_weather(location):
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': location, 'appid': WEATHER_API_KEY, 'units': 'metric'}
    
    try:
        res = requests.get(url, params=params)
        data = res.json()

        if data.get('cod') != 200:
            return f"Sorry, I couldn't find weather info for '{location}'."

        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        city = data['name']
        return f"The weather in {city} is {weather} with a temperature of {temp}°C."

    except Exception as e:
        return "Sorry, I'm having trouble retrieving the weather info right now."

def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        message = message.translate(str.maketrans('', '', string.punctuation)).strip()
        session_id = request.session.session_key or "default"

        # 1. Weather location reply handling
        if weather_pending_sessions.get(session_id):
            weather_pending_sessions[session_id] = False
            weather_info = get_weather(message)
            return JsonResponse({'response': weather_info})

        # 2. Multi-step note-taking
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
                    os.system(f"notepad.exe {filepath}")  # Windows only
                except Exception:
                    pass

                return JsonResponse({'response': f"Note '{title}' saved and opened in Notepad!"})
                
        raw_message = request.POST.get('message', '').lower().strip()
        message = raw_message.translate(str.maketrans('', '', string.punctuation)).strip()

        if raw_message.startswith("open ") and raw_message.endswith(".txt"):
            filename = raw_message[5:].strip()
            filename = filename.replace(" ", "_")
            filepath = os.path.abspath(os.path.join("notes", filename))

            if os.path.isfile(filepath):
                try:
                    subprocess.Popen(['notepad.exe', filepath])
                    response = f"Opening note '{filename}' in Notepad."
                except Exception as e:
                    response = f"Note '{filename}' found, but failed to open it. Error: {str(e)}"
            else:
                response = f"Sorry, note '{filename}' does not exist."

            return JsonResponse({'response': response})

    if message:
        # 3. Weather command
        if message == "weather":
            weather_pending_sessions[session_id] = True
            return JsonResponse({'response': "Please enter the name of a location to get the weather."})

        # 4. Start a new note
        if message == "new note":
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

        # Command handling
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
        elif "weather" in message:
            weather_pending_sessions[session_id] = True
            response = "Sure! For which location would you like the weather?"
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
