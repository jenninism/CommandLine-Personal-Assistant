import wikipedia
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import string
import datetime

def chat_page(request):
    return render(request, 'clpaapp/chat.html')

@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        message = message.translate(str.maketrans('', '', string.punctuation)).strip()

        replies = {
            "hi": "Hello!",
            "hello": "Hi there!",
            "how are you": "I'm just code, but thanks for asking!",
            "what can you do": "I can answer questions, give daily advice, and open websites.",
            "who are you": "I am your Command Line Personal Assistant.",
            "what is your name": "You can call me CLPA!",
            "bye": "Goodbye!",
            "thank you": "You're welcome!",
            "yow": "Hi there!",
            "what time is it": "I'm not wearing a watch, but your taskbar might help.",
            "what is programming language": "Programming languages are like a puzzle box, and I'm the puzzle solver.",
            "what is html": "HTML is a markup language for structuring web content.",
            "what is css": "CSS is a style sheet language for styling HTML elements.",
            "what is javascript": "JavaScript is a programming language for adding interactivity to web pages.",
            "what is git": "Git is a distributed version control system for tracking changes in source code.",
            "what is github": "GitHub is a web-based platform for hosting and collaborating on version control repositories.",
            "what is linux": "Linux is an open-source operating system based on the Unix operating system.",
            "what is windows": "Windows is a popular operating system for personal computers.",
            "what is macos": "macOS is a user-friendly operating system for Mac computers.",
            "what is android": "Android is a mobile operating system based on the Linux kernel.",
            "what is ios": "iOS is a mobile operating system for Apple devices.",
            "what is react": "React is a JavaScript library for building user interfaces.",
            "what is vue": "Vue.js is a progressive JavaScript framework for building user interfaces.",
            "what is angular": "Angular is a TypeScript-based framework for building modern web applications.",
            "what is node": "Node.js is a JavaScript runtime environment for building server-side applications.",
            "how to write a program": "You can use a text editor like Notepad or Visual Studio Code.",
            "how to install python": "You can use a package manager like pip or conda.",
            "how to install django": "You can use a package manager like pip or conda.",
            "what is pip?":"",
            "what is python": "Python is a beginner-friendly programming language.",
            "what is django": "Django is a Python web framework for building powerful websites.",
            "how old are you": "I'm timeless—just a few lines of code.",
            "do you sleep": "Nope, I run 24/7 just for you.",
            "can you be my friend": "Of course! I'm always here.",
            "do you love me": "01011001 01000101 01010011 ❤️",
            "what should i eat": "Try chicken adobo or instant pancit canton!",
            "i'm bored": "Want a fun fact or to open YouTube?",
            "i'm tired": "Take a short break, you deserve it.",
            "i'm hungry": "Try a healthy snack or a quick meal.",
            "i'm sad": "Have a cup of tea or listen to music.",
            "i'm happy": "Celebrate with a party or a movie.",
            "i'm tired": "Take a short break, you deserve it.",
            "help": None  # handled separately
        }

        websites = {
            "open google": "https://www.google.com",
            "open youtube": "https://www.youtube.com",
            "open facebook": "https://www.facebook.com",
            "open twitter": "https://www.twitter.com",
            "open gmail": "https://mail.google.com",
            "open github": "https://github.com",
            "open instagram": "https://www.instagram.com",
            "open messenger": "https://www.messenger.com",
            "open yahoo": "https://www.yahoo.com",
            "open microsoft": "https://www.microsoft.com",
            "open stackoverflow": "https://stackoverflow.com"
        }

        url = None
        response = None

        # Check if the message is a command
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
            response = "You can ask me things like:\n- " + "\n- ".join(
                sorted(list(replies.keys()) + list(websites.keys()) + ["clear", "exit", "time", "date"])
            )
        elif message in websites:
            url = websites[message]
            response = f"Opening {message.split()[-1].capitalize()}..."
        else:
            # Check if the message is a question
            if any(message.startswith(prefix) for prefix in ["who is", "what is", "where is", "who was", "what are", "who are"]):
                try:
                    # Try to get the answer from Wikipedia
                    summary = wikipedia.summary(message, sentences=2)
                    response = summary
                except wikipedia.DisambiguationError as e:
                    response = f"Your query is ambiguous, did you mean: {', '.join(e.options[:5])}?"
                except wikipedia.PageError:
                    response = "Sorry, I couldn't find any information on that."
                except Exception:
                    response = "Sorry, I had trouble searching for that."
            else:
                # fallback to predefined replies
                response = replies.get(message, "Sorry, I don't understand.")

        return JsonResponse({'response': response, 'url': url})

    else:
        return JsonResponse({'error': 'Invalid method'}, status=400)
