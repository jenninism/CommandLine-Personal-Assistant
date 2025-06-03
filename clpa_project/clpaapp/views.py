import wikipedia
import string
import datetime
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import subprocess
import requests
import webbrowser

folder_pending_sessions = {}
note_pending_sessions = {}  # NOTES

def get_definition(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)
        data = response.json()

        if isinstance(data, dict) and data.get("title") == "No Definitions Found":
            return f"Sorry, I couldn't find a definition for '{word}'."

        meanings = data[0]['meanings']
        definitions = []

        for meaning in meanings:
            part_of_speech = meaning.get('partOfSpeech', '')
            for definition in meaning['definitions']:
                def_text = definition['definition']
                example = definition.get('example', '')
                line = f"{part_of_speech}: {def_text}"
                if example:
                    line += f" (Example: {example})"
                definitions.append(line)

        return "\n".join(definitions[:3])  # limit to 3 definitions for brevity
    except Exception:
        return "Sorry, I couldn't retrieve the definition right now."


def chat_page(request):
    return render(request, 'clpaapp/chat.html')

def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        message = message.translate(str.maketrans('', '', string.punctuation)).strip()
        session_id = request.session.session_key or "default"
    
        timer_match = re.search(r"set timer for (\d+)\s*(seconds?|minutes?|hours?)", message)
        if timer_match:
            amount = int(timer_match.group(1))
            unit = timer_match.group(2)
            return JsonResponse({'response': f"⏱ Timer set for {amount} {unit}!"})

        if any(phrase in message for phrase in ["timer", "i need timer", "please timer"]):
            return JsonResponse({'response': "How long should I set the timer for? (e.g., 'set timer for 5 minutes')"})
        
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
        if session_id in folder_pending_sessions:
            folder_name = message.strip()
            FOLDER_DIR = os.path.join(os.path.expanduser("~"), "CLPA_Folders")
            os.makedirs(FOLDER_DIR, exist_ok=True)

            folder_path = os.path.join(FOLDER_DIR, folder_name)
            try:
                os.makedirs(folder_path)
                os.startfile(folder_path)
                response = f"Folder '{folder_name}' has been created in {FOLDER_DIR}."
            except FileExistsError:
                response = f"A folder named '{folder_name}' already exists."
            except Exception as e:
                response = f"Failed to create folder: {e}"

            del folder_pending_sessions[session_id]
            return JsonResponse({'response': response})
                        
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

            # 4. Start a new note
        if message == "new note":
            note_pending_sessions[session_id] = {"step": "title", "title": ""}
            return JsonResponse({'response': "Sure! What should the title of the note be?"})
                
        if raw_message.startswith("delete ") and raw_message.endswith(".txt"):
            filename = raw_message[7:].strip()  # remove 'delete ' part
            filename = filename.replace(" ", "_")
            filepath = os.path.abspath(os.path.join("notes", filename))

            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    response = f"Note '{filename}' deleted!"
                except Exception as e:
                    response = f"Failed to delete note '{filename}'. Error: {str(e)}"
            else:
                response = f"Note '{filename}' does not exist."

            return JsonResponse({'response': response})


        # Static responses
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

        # Website shortcuts
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
        elif message.startswith("define "):
            word = message.replace("define ", "").strip()
            if word:
                response = get_definition(word)
            else:
                response = "Please tell me the word you want me to define."
        elif message in ["create folder", "new folder", "make folder"]:
            folder_pending_sessions[session_id] = True
            response = "What should the folder name be?"
        elif message.startswith("open folder "):
            folder_name = message.replace("open folder", "").strip()
            FOLDER_DIR = os.path.join(os.path.expanduser("~"), "CLPA_Folders")
            folder_path = os.path.join(FOLDER_DIR, folder_name)

            if os.path.isdir(folder_path):
                try:
                    os.startfile(folder_path)
                    response = f"Opening folder '{folder_name}'..."
                except Exception:
                    response = f"Found the folder, but I couldn't open it."
            else:
                response = f"Sorry, the folder '{folder_name}' does not exist."
        elif message.startswith("search "):
            query = message.replace("search", "").strip()
            if query:
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                try:
                    response = f"Searching for '{query}' on Google..."
                except Exception:
                    response = f"Something went wrong while trying to search."
            else:
                response = "What would you like me to search for?"



        else:
            response = replies.get(message, "Sorry, I don't understand that yet.")

        return JsonResponse({'response': response, 'url': url})

    return JsonResponse({'error': 'Invalid method'}, status=400)
