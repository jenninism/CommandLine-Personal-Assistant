import requests
import ast
import operator
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import webbrowser
from urllib.parse import urlparse, quote_plus
import threading
import time
# from win10toast import ToastNotifier

import os
import subprocess
from pathlib import Path

import tempfile

# toaster = ToastNotifier()
REMINDERS = {}

def chat_page(request):
    return render(request, 'clpaapp/chat.html')

# def reminder_checker():
#     while True:
#         now = datetime.now()
#         for session_key, reminders in list(REMINDERS.items()):
#             for reminder in reminders[:]:  # copy list to avoid mutation issues
#                 dt = datetime.strptime(reminder['date'] + ' ' + reminder['time'], '%Y-%m-%d %H:%M')
#                 if now >= dt:
#                     # Show notification
#                     toaster.show_toast(
#                         "Reminder",
#                         f"{reminder['title']} at {reminder['location']}",
#                         duration=10
#                     )
#                     reminders.remove(reminder)
#             if not reminders:
#                 REMINDERS.pop(session_key)
#         time.sleep(30)

# # Start background thread on server start
# threading.Thread(target=reminder_checker, daemon=True).start()


@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        session_key = request.session.session_key or request.session.create()
        message = request.POST.get('message', '').strip()
        low_msg = message.lower()

        # Retrieve current reminder state and data from session
        reminder_state = request.session.get('reminder_state', None)
        reminder_data = request.session.get('reminder_data', {})

        if low_msg == 'add reminder':
            request.session['reminder_state'] = 'waiting_title'
            request.session['reminder_data'] = {}
            response = "What kind of reminder? Please tell me the title."

        elif low_msg == 'show reminders':
            reminders = REMINDERS.get(session_key, [])
            if not reminders:
                response = "You have no reminders."
            else:
                response_lines = ["Your reminders:"]
                for i, rem in enumerate(reminders, 1):
                    line = (f"{i}. {rem['title']} at {rem['location']} on {rem['date']} at {rem['time']}")
                    response_lines.append(line)
                response = "\n".join(response_lines)
                
        # Start deletion flow: user says "delete reminder"
        elif low_msg == 'delete reminder':
            reminders = REMINDERS.get(session_key, [])
            if not reminders:
                response = "You have no reminders to delete."
            else:
                # Save deletion state and show reminders list
                request.session['delete_state'] = 'awaiting_number'
                response_lines = ["Which reminder number do you want to delete?"]
                for i, rem in enumerate(reminders, 1):
                    response_lines.append(f"{i}. {rem['title']} at {rem['location']} on {rem['date']} at {rem['time']}")
                response = "\n".join(response_lines)

        # If deletion state awaiting number
        elif request.session.get('delete_state') == 'awaiting_number':
            reminders = REMINDERS.get(session_key, [])
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(reminders):
                    removed = reminders.pop(idx)
                    REMINDERS[session_key] = reminders
                    response = (f"Deleted reminder: {removed['title']} at {removed['location']} "
                                f"on {removed['date']} {removed['time']}.")
                    request.session['delete_state'] = None  # Clear deletion state
                else:
                    response = "Invalid number. Please enter a valid reminder number."
            else:
                response = "Please enter a valid reminder number."



        elif reminder_state == 'waiting_title':
            reminder_data['title'] = message
            request.session['reminder_data'] = reminder_data
            request.session['reminder_state'] = 'waiting_location'
            response = "Where is the location?"

        elif reminder_state == 'waiting_location':
            reminder_data['location'] = message
            request.session['reminder_data'] = reminder_data
            request.session['reminder_state'] = 'waiting_date'
            response = "When is the date? (YYYY-MM-DD)"

        elif reminder_state == 'waiting_date':
            try:
                datetime.strptime(message, '%Y-%m-%d')
                reminder_data['date'] = message
                request.session['reminder_data'] = reminder_data
                request.session['reminder_state'] = 'waiting_time'
                response = "What time? (HH:MM, 24-hour)"
            except ValueError:
                response = "Please enter a valid date in YYYY-MM-DD format."

        elif reminder_state == 'waiting_time':
            try:
                datetime.strptime(message, '%H:%M')
                reminder_data['time'] = message
                request.session['reminder_data'] = reminder_data

                # Save reminder to global REMINDERS dict
                reminders = REMINDERS.get(session_key, [])
                reminders.append(reminder_data)
                REMINDERS[session_key] = reminders

                # Clear session state
                request.session['reminder_state'] = None
                request.session['reminder_data'] = {}

                response = (f"Successfully created! Reminder for {reminder_data['date']}, "
                            f"{reminder_data['time']} at {reminder_data['location']}")
            except ValueError:
                response = "Please enter a valid time in HH:MM 24-hour format."
        # Start edit flow
        elif low_msg == 'edit reminder':
            reminders = REMINDERS.get(session_key, [])
            if not reminders:
                response = "You have no reminders to edit."
            else:
                request.session['edit_state'] = 'awaiting_number'
                response_lines = ["Which reminder number do you want to edit?"]
                for i, rem in enumerate(reminders, 1):
                    response_lines.append(f"{i}. {rem['title']} at {rem['location']} on {rem['date']} at {rem['time']}")
                response = "\n".join(response_lines)

        # Continue edit flow
        elif request.session.get('edit_state') == 'awaiting_number':
            reminders = REMINDERS.get(session_key, [])
            if message.isdigit():
                idx = int(message) - 1
                if 0 <= idx < len(reminders):
                    request.session['edit_index'] = idx
                    request.session['edit_state'] = 'awaiting_title'
                    response = "What is the new title?"
                else:
                    response = "Invalid number. Please enter a valid reminder number."
            else:
                response = "Please enter a valid reminder number."

        elif request.session.get('edit_state') == 'awaiting_title':
            request.session['edit_data'] = {'title': message}
            request.session['edit_state'] = 'awaiting_location'
            response = "New location?"

        elif request.session.get('edit_state') == 'awaiting_location':
            request.session['edit_data']['location'] = message
            request.session['edit_state'] = 'awaiting_date'
            response = "New date (YYYY-MM-DD)?"

        elif request.session.get('edit_state') == 'awaiting_date':
            request.session['edit_data']['date'] = message
            request.session['edit_state'] = 'awaiting_time'
            response = "New time (HH:MM)?"

        elif request.session.get('edit_state') == 'awaiting_time':
            reminders = REMINDERS.get(session_key, [])
            idx = request.session.get('edit_index')
            edit_data = request.session.get('edit_data', {})
            edit_data['time'] = message
            if 0 <= idx < len(reminders):
                reminders[idx] = edit_data
                REMINDERS[session_key] = reminders
                response = (f"Reminder updated!\n"
                            f"{edit_data['title']} at {edit_data['location']} on {edit_data['date']} {edit_data['time']}")
            else:
                response = "Something went wrong. Please try again."
            # Clear session edit state
            request.session['edit_state'] = None
            request.session['edit_data'] = None
            request.session['edit_index'] = None

        elif low_msg == 'search folder':
            request.session['folder_search_state'] = 'awaiting_location_choice'
            response = "Where do you want me to search? (Documents, Desktop)"

        # Get location to search in
        elif request.session.get('folder_search_state') == 'awaiting_location_choice':
            location = message.lower()
            if location == 'documents':
                request.session['folder_base_path'] = str(Path.home() / "Documents")
            elif location == 'desktop':
                request.session['folder_base_path'] = str(Path.home() / "Desktop")
            else:
                response = "Please choose either 'Documents' or 'Desktop'."
                return JsonResponse({'response': response})

            request.session['folder_search_state'] = 'awaiting_folder_name'
            response = "What folder name are you looking for?"

        # Get folder name and search
        elif request.session.get('folder_search_state') == 'awaiting_folder_name':
            folder_name = message
            base_path = request.session.get('folder_base_path')
            found_path = None

            for root, dirs, files in os.walk(base_path):
                if folder_name in dirs:
                    found_path = os.path.join(root, folder_name)
                    break

            if found_path:
                subprocess.Popen(f'explorer "{found_path}"')
                response = f"Found and opening: {found_path}"
            else:
                response = f"Sorry, I couldn't find a folder named '{folder_name}' in that location."

            # Clear session state
            request.session['folder_search_state'] = None
            request.session['folder_base_path'] = None

        elif low_msg == 'create folder':
            request.session['folder_create_state'] = 'awaiting_folder_name'
            response = "What do you want to name the folder?"

        elif request.session.get('folder_create_state') == 'awaiting_folder_name':
            request.session['new_folder_name'] = message.strip()
            request.session['folder_create_state'] = 'awaiting_location'
            response = "Where do you want to create it? (Documents, Desktop)"

        elif request.session.get('folder_create_state') == 'awaiting_location':
            location = message.strip().lower()
            folder_name = request.session.get('new_folder_name')

            if location == 'documents':
                base_path = Path.home() / "Documents"
            elif location == 'desktop':
                base_path = Path.home() / "Desktop"
            else:
                response = "Please choose either 'Documents' or 'Desktop'."
                return JsonResponse({'response': response})

            full_path = base_path / folder_name

            try:
                os.makedirs(full_path, exist_ok=True)
                subprocess.Popen(f'explorer "{full_path}"')
                response = f"Folder '{folder_name}' created in {location.capitalize()}!"
            except Exception as e:
                response = f"Sorry, there was an error creating the folder: {e}"

            # Clear session state
            request.session['folder_create_state'] = None
            request.session['new_folder_name'] = None

        elif low_msg == 'create note':
            request.session['note_create_state'] = 'awaiting_title'
            response = "What is the title of your note?"

        elif request.session.get('note_create_state') == 'awaiting_title':
            request.session['note_title'] = message.strip()
            request.session['note_create_state'] = 'awaiting_content'
            response = "What should the note say?"

        elif request.session.get('note_create_state') == 'awaiting_content':
            request.session['note_content'] = message.strip()
            request.session['note_create_state'] = 'awaiting_location'
            response = "Where do you want to save it? (Documents or Desktop)"

        elif request.session.get('note_create_state') == 'awaiting_location':
            location = message.strip().lower()
            note_title = request.session.get('note_title')
            note_content = request.session.get('note_content')

            if location == 'documents':
                save_path = Path.home() / "Documents"
            elif location == 'desktop':
                save_path = Path.home() / "Desktop"
            else:
                response = "Please choose either 'Documents' or 'Desktop'."
                return JsonResponse({'response': response})

            full_path = save_path / f"{note_title}.txt"

            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(note_content)
                subprocess.Popen(['notepad.exe', str(full_path)])
                response = f"Note '{note_title}' saved to {location.capitalize()} and opened in Notepad!"
            except Exception as e:
                response = f"Sorry, I couldn't create the note: {e}"

            # Clear session state
            request.session['note_create_state'] = None
            request.session['note_title'] = None
            request.session['note_content'] = None

                        
            


        # Existing commands if no reminder flow active
        elif low_msg == 'hello':
            response = "Hi! How can I help you today?"
        elif low_msg == 'date':
            response = datetime.now().strftime("Today's date is %Y-%m-%d.")
        elif low_msg == 'time':
            response = datetime.now().strftime("Current time is %H:%M:%S.")
        elif low_msg == 'help':
            response = (
                "Commands Available:\n"
                "- time\n"
                "- date\n"
                "- help\n"
                "- calculate\n"
                "- define (word)\n"
                "- open (website)\n"
                "- add reminder\n"
                "- show reminders\n"
                "- edit reminder\n"
                "- delete reminder\n"
                "- create note\n"
                "- create folder\n"               
                "- search folder\n"
            )
        elif low_msg.startswith('define '):
            word = message[7:].strip()
            response = get_definition(word)
        elif low_msg.startswith('calculate '):
            expr = message[10:].strip()
            response = calculate_expression(expr)
        elif low_msg.startswith('open '):
            query = message[5:].strip()
            success = open_in_chrome(query)
            if success:
                response = f"Opening Chrome and searching for: {query}"
            else:
                response = "Sorry, I couldn't open the browser."
        else:
            response = "Sorry, I don't understand that yet."

        return JsonResponse({'response': response})

    return JsonResponse({'error': 'Invalid method'}, status=400)


def get_definition(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and data:
                meanings = data[0].get('meanings', [])
                if meanings:
                    definitions = meanings[0].get('definitions', [])
                    if definitions:
                        definition_text = definitions[0].get('definition', '')
                        return f"Definition of {word}:\n{definition_text}"
            return f"Sorry, I couldn't find a definition for '{word}'."
        else:
            return f"Sorry, I couldn't find a definition for '{word}'."
    except Exception:
        return "Sorry, there was an error retrieving the definition."


def calculate_expression(expr):
    try:
        node = ast.parse(expr, mode='eval')

        def eval_node(n):
            operators = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos,
                ast.Mod: operator.mod,
            }
            if isinstance(n, ast.Expression):
                return eval_node(n.body)
            elif isinstance(n, ast.BinOp):
                left = eval_node(n.left)
                right = eval_node(n.right)
                op = operators[type(n.op)]
                return op(left, right)
            elif isinstance(n, ast.UnaryOp):
                operand = eval_node(n.operand)
                op = operators[type(n.op)]
                return op(operand)
            elif isinstance(n, ast.Num):
                return n.n
            elif isinstance(n, ast.Constant):  # For Python 3.8+
                if isinstance(n.value, (int, float)):
                    return n.value
                else:
                    raise ValueError("Unsupported constant")
            else:
                raise ValueError("Unsupported expression")

        result = eval_node(node)
        return f"The result is: {result}"
    except Exception:
        return "Sorry, I couldn't calculate that expression."


def open_in_chrome(query):
    try:
        parsed = urlparse(query)
        if parsed.scheme in ['http', 'https']:
            url = query
        else:
            search_query = quote_plus(query)
            url = f"https://www.google.com/search?q={search_query}"

        webbrowser.open_new_tab(url)
        return True
    except Exception as e:
        print(f"Error opening browser: {e}")
        return False
