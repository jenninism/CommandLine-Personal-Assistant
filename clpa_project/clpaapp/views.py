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
from win10toast import ToastNotifier

toaster = ToastNotifier()
REMINDERS = {}

def chat_page(request):
    return render(request, 'clpaapp/chat.html')

def reminder_checker():
    while True:
        now = datetime.now()
        for session_key, reminders in list(REMINDERS.items()):
            for reminder in reminders[:]:  # copy list to avoid mutation issues
                dt = datetime.strptime(reminder['date'] + ' ' + reminder['time'], '%Y-%m-%d %H:%M')
                if now >= dt:
                    # Show notification
                    toaster.show_toast(
                        "Reminder",
                        f"{reminder['title']} at {reminder['location']}",
                        duration=10
                    )
                    reminders.remove(reminder)
            if not reminders:
                REMINDERS.pop(session_key)
        time.sleep(30)

# Start background thread on server start
threading.Thread(target=reminder_checker, daemon=True).start()


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
                "- definition\n"
                "- open (website)\n"
                "- add reminder\n"
                "- show reminders\n"
                "- edit reminder\n"
                "- delete reminder"
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
