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
import math 
import json

folder_pending_sessions = {}
note_pending_sessions = {}  # NOTES
folder_search_sessions = {}
reminder_pending_sessions = {} 

def load_reminders(session_id):
    filepath = f'reminders_{session_id}.json'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return []

def save_reminders(session_id, reminders):
    filepath = f'reminders_{session_id}.json'
    with open(filepath, 'w') as f:
        json.dump(reminders, f)

def find_folders(root_path, folder_name):
    matches = []
    for dirpath, dirnames, _ in os.walk(root_path):
        if folder_name in dirnames:
            full_path = os.path.join(dirpath, folder_name)
            matches.append(full_path)
    return matches

def open_folders_by_name(folder_name):
    drives = ['%s:\\' % d for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists('%s:\\' % d)]
    found_folders = []
    for drive in drives:
        found_folders.extend(find_folders(drive, folder_name))

    if not found_folders:
        return f"❌ No folders named '{folder_name}' found."

    for folder_path in found_folders:
        try:
            os.startfile(folder_path)
        except Exception:
            pass

    return f"📂 Opened {len(found_folders)} folder(s) named '{folder_name}'."


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

        return "\n".join(definitions[:3])  
    except Exception:
        return "Sorry, I couldn't retrieve the definition right now."


def chat_page(request):
    return render(request, 'clpaapp/chat.html')

def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()
        message = message.translate(str.maketrans('', '', string.punctuation)).strip()
        session_id = request.session.session_key or "default"

#DEFINE
        if message.startswith("define "):
            word = message.replace("define ", "").strip()
            if word:
                response_text = get_definition(word)
            else:
                response_text = "Please tell me the word you want me to define."
            return JsonResponse({'response': response_text})
#TIME
        if message == "time":
            now = datetime.datetime.now()
            response_text = "Current time is " + now.strftime("%H:%M:%S")
            return JsonResponse({'response': response_text})
#DATE
        elif message == "date":
            today = datetime.date.today()
            response_text = "Today's date is " + today.strftime("%B %d, %Y")
            return JsonResponse({'response': response_text})

#REMINDERS
        if message == "reminders":
            reminders = load_reminders(session_id)
            if reminders:
                response_text = "Here are your reminders:\n" + "\n".join(f"- {r}" for r in reminders)
            else:
                response_text = "You have no reminders."
            return JsonResponse({'response': response_text})

#EDIT REMINDERS
        if message == "edit reminders":
            reminders = load_reminders(session_id)
            if not reminders:
                return JsonResponse({'response': "You have no reminders to edit."})
            reminders_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(reminders)])
            reminder_pending_sessions[session_id] = {"mode": "edit", "step": "choose_index"}
            return JsonResponse({'response': f"Here are your reminders:\n{reminders_list}\nWhich one would you like to edit? (Please reply with the reminder number)"})

        # Handle ongoing add/edit sessions
        if session_id in reminder_pending_sessions:
            session_data = reminder_pending_sessions[session_id]
            mode = session_data.get("mode")

            reminders = load_reminders(session_id)

            # Adding reminder: user just sends the reminder text
            if mode == "add":
                reminders.append(message)
                save_reminders(session_id, reminders)
                del reminder_pending_sessions[session_id]
                return JsonResponse({'response': f"Got it! Reminder added: '{message}'"})

            # Editing reminder
            elif mode == "edit":
                step = session_data.get("step")

                if step == "choose_index":
                    try:
                        index = int(message) - 1
                        if index < 0 or index >= len(reminders):
                            return JsonResponse({'response': "Invalid reminder number. Please try again."})
                        session_data["edit_index"] = index
                        session_data["step"] = "new_text"
                        return JsonResponse({'response': f"Please enter the new text for reminder #{index+1}."})
                    except ValueError:
                        return JsonResponse({'response': "Please enter a valid number."})

                elif step == "new_text":
                    index = session_data["edit_index"]
                    reminders[index] = message  # Update reminder text
                    save_reminders(session_id, reminders)
                    del reminder_pending_sessions[session_id]
                    return JsonResponse({'response': f"Reminder #{index+1} updated successfully!"})
                
        if message == "delete reminders":
            reminders = load_reminders(session_id)
            if not reminders:
                return JsonResponse({'response': "You have no reminders to delete."})
            reminders_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(reminders)])
            reminder_pending_sessions[session_id] = {"mode": "delete", "step": "choose_index"}
            return JsonResponse({'response': f"Here are your reminders:\n{reminders_list}\nWhich one would you like to delete? (Please reply with the reminder number)"})

        # Handle ongoing delete reminder session
        if session_id in reminder_pending_sessions:
            session_data = reminder_pending_sessions[session_id]
            mode = session_data.get("mode")

            if mode == "delete":
                step = session_data.get("step")
                reminders = load_reminders(session_id)

                if step == "choose_index":
                    try:
                        index = int(message) - 1
                        if index < 0 or index >= len(reminders):
                            return JsonResponse({'response': "Invalid reminder number. Please try again."})

                        deleted_reminder = reminders.pop(index)
                        save_reminders(session_id, reminders)
                        del reminder_pending_sessions[session_id]
                        return JsonResponse({'response': f"Deleted reminder: '{deleted_reminder}'"})
                    except ValueError:
                        return JsonResponse({'response': "Please enter a valid number."})
                    
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
    
        if message.startswith("calculate "):
            expression = raw_message[len("calculate "):].strip()

            # Allow only digits, math operators, parentheses, and spaces
            allowed_chars = "0123456789+-*/(). "
            if any(ch not in allowed_chars for ch in expression):
                response = "Sorry, I can only calculate simple math expressions with numbers and +, -, *, /, ( )."
            else:
                try:
                    # Evaluate safely with eval limited to math builtins only
                    result = eval(expression, {"__builtins__": None}, {})
                    response = f"Result: {result}"
                except Exception as e:
                    response = f"Error calculating expression: {str(e)}"

            return JsonResponse({'response': response})
        
        if session_id in reminder_pending_sessions:
            # Add the reminder text
            reminders = load_reminders(session_id)
            reminders.append(message)
            save_reminders(session_id, reminders)
            del reminder_pending_sessions[session_id]
            return JsonResponse({'response': f"Got it! Reminder added: '{message}'"})
     

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
            "what is programming language": "Programming languages are tools for writing instructions to computers.",
            "what is pip": "Pip is a package manager for Python packages.",
            "what is python": "Python is a popular programming language that's beginner-friendly.",
            "what is django": "Django is a high-level Python web framework for building websites.",
            "do you love me": "01011001 01000101 01010011 ❤️",
            "help": "List of available commands:\n-new note\n-open note\n-delete note\n-time\n-date\n-timer\n-reminders\n-add reminder\n-edit reminders\n-delete reminders\n-create folder\n-open folder 'file name'\n-define (something)\n-open (website)\n-open (application)\n-clear\n-exit\n",
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

        
        if message in websites:
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

        
        if session_id in folder_pending_sessions:
            stage = folder_pending_sessions[session_id]["awaiting"]

            if stage == "location":
                location = message.strip().lower()

                # Map user-friendly names to system paths
                if location == "desktop":
                    base_path = os.path.join(os.path.expanduser("~"), "Desktop")
                elif location == "documents":
                    base_path = os.path.join(os.path.expanduser("~"), "Documents")
                elif os.path.isabs(location):
                    base_path = location
                else:
                    base_path = os.path.join(os.path.expanduser("~"), location)

                folder_pending_sessions[session_id] = {
                    "awaiting": "name",
                    "base_path": base_path
                }
                return JsonResponse({'response': "Got it! What should the folder name be?"})

            elif stage == "name":
                name = message.strip()
                base_path = folder_pending_sessions[session_id]["base_path"]
                folder_path = os.path.join(base_path, name)

                try:
                    os.makedirs(folder_path, exist_ok=True)
                    response = f"Folder created at: {folder_path}"
                except Exception as e:
                    response = f"Failed to create folder: {e}"

                del folder_pending_sessions[session_id]
                return JsonResponse({'response': response})

        elif message in ["create folder", "new folder", "make folder"]:
            folder_pending_sessions[session_id] = {"awaiting": "location"}
            response = "📂 Where would you like to place the folder? (e.g. Desktop, Documents, D:\\MyProjects)"

        
        elif message.startswith("search "):
            query = message.replace("search", "").strip()
            if query:
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                response = f"Searching for '{query}' on Google..."
                return JsonResponse({'response': response, 'url': url})  # ✅ return early
            else:
                response = "What would you like me to search for?"
                return JsonResponse({'response': response})
            
        if session_id in folder_search_sessions:
            session = folder_search_sessions[session_id]

            if session["step"] == "ask_location":
                location = message.strip()

                # Resolve location to full path
                if location.lower() == "desktop":
                    base_path = os.path.join(os.path.expanduser("~"), "Desktop")
                elif location.lower() == "documents":
                    base_path = os.path.join(os.path.expanduser("~"), "Documents")
                elif os.path.isabs(location):
                    base_path = location
                else:
                    base_path = os.path.join(os.path.expanduser("~"), location)

                folder_name = session["folder_name"]
                try:
                    found_folders = find_folders(base_path, folder_name)
                    if not found_folders:
                        response = f"❌ No folders named '{folder_name}' found in {base_path}."
                    else:
                        for folder_path in found_folders:
                            subprocess.Popen(['explorer', folder_path])
                        response = f"📂 Opened {len(found_folders)} folder(s) named '{folder_name}' in {base_path}."
                except Exception as e:
                    response = f"Error searching folders: {e}"

                del folder_search_sessions[session_id]
                return JsonResponse({'response': response})



        if message.startswith("open folder "):
            folder_name = message[len("open folder "):].strip()
            folder_search_sessions[session_id] = {"step": "ask_location", "folder_name": folder_name}
            response = f"Where should I look for the folder named '{folder_name}'? (e.g., Desktop, Documents, D:\\MyProjects)"
            return JsonResponse({'response': response})



        elif message.startswith("open "):
            app = message.replace("open", "").strip().lower()
        
            app_paths = {
                "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                "spotify": r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",
                "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                "notepad": "notepad",
                "calculator": "calc",
                "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
                "folder": os.path.expanduser("~"),

                "outlook": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
                "paint": r"C:\Windows\System32\mspaint.exe",
                "wordpad": r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
            }
            

            if app in app_paths:
                try:
                    subprocess.Popen(app_paths[app] if "\\" in app_paths[app] else [app_paths[app]])
                    response = f"Opening {app.capitalize()}..."
                except Exception as e:
                    response = f"Failed to open {app}: {e}"
            else:
                response = f"Sorry, I don't know how to open '{app}'."
        elif message.startswith("open ") and message.endswith(".exe"):
            exe_path = message.replace("open", "").strip()
            if os.path.isfile(exe_path):
                os.startfile(exe_path)
                response = f"Opening application at {exe_path}"
            else:
                response = f"No application found at {exe_path}"




        else:
            response = replies.get(message, "Sorry, I don't understand that yet.")

        return JsonResponse({'response': response, 'url': url})

    return JsonResponse({'error': 'Invalid method'}, status=400)

        