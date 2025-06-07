import os
import json
import threading
import time
from datetime import datetime, timedelta
from win10toast import ToastNotifier

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.apps import AppConfig

class ClpaappConfig(AppConfig):
    name = 'clpaapp'

    def ready(self):
        print("[apps.py] ready() called - starting reminder checker thread")
        from .views import start_reminder_checker
        threading.Thread(target=start_reminder_checker, daemon=True).start()

# Reminder file helpers
def get_filepath(session_id):
    return f"reminders_{session_id}.json"

def load_reminders(session_id):
    filepath = get_filepath(session_id)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def save_reminders(session_id, reminders):
    filepath = get_filepath(session_id)
    with open(filepath, "w") as f:
        json.dump(reminders, f, indent=2)

# Notification checker function (runs forever in background)
def check_reminders(session_id):
    toaster = ToastNotifier()
    print("[Reminder Checker] Started")
    while True:
        reminders = load_reminders(session_id)
        now = datetime.now()
        print(f"[Reminder Checker] Now: {now}, Loaded {len(reminders)} reminders")
        changed = False
        for reminder in reminders:
            if not isinstance(reminder, dict):
                print(f"[Reminder Checker] Skipping invalid reminder (not dict): {reminder}")
                continue

            if reminder.get("notified"):
                continue
            try:
                reminder_dt = datetime.strptime(f"{reminder['date']} {reminder['time']}", "%Y-%m-%d %H:%M")
            except Exception as e:
                print(f"[Reminder Checker] Invalid date/time format: {reminder} - {e}")
                continue

            if reminder_dt <= now < reminder_dt + timedelta(minutes=1):
                message = f"{reminder['title']} at {reminder['location']}"
                print(f"[Reminder Checker] Showing notification: {message}")
                toaster.show_toast("Reminder", message, duration=10)
                reminder["notified"] = True
                changed = True

        if changed:
            save_reminders(session_id, reminders)

        time.sleep(30)  # check every 30 seconds

# Start background thread function (called from apps.py ready)
def start_reminder_checker():
    session_id = "default"
    def run_checker():
        check_reminders(session_id)
    threading.Thread(target=run_checker, daemon=True).start()
    print("[Reminder Bot] Reminder checker thread started.")


# Session state for multi-step conversation
reminder_sessions = {}

def handle_message(session_id, message):
    if session_id not in reminder_sessions:
        reminder_sessions[session_id] = {"step": None, "data": {}}

    session = reminder_sessions[session_id]
    message_lower = message.lower()

    if message_lower in [":delete reminder", "delete reminder"]:
        reminders = load_reminders(session_id)
        if not reminders:
            return "You have no reminders to delete."

        session["step"] = "delete_select"
        session["data"] = {}
        lines = []
        for idx, r in enumerate(reminders):
            lines.append(f"{idx + 1}. {r.get('title', '(no title)')} on {r.get('date')} at {r.get('time')}")
        return "Which reminder would you like to delete?\n" + "\n".join(lines)

    if session["step"] == "delete_select":
        try:
            index = int(message) - 1
            reminders = load_reminders(session_id)
            if 0 <= index < len(reminders):
                removed = reminders.pop(index)
                save_reminders(session_id, reminders)
                reminder_sessions.pop(session_id)
                return f"Deleted reminder: {removed.get('title', '(no title)')} on {removed.get('date')} at {removed.get('time')}"
            else:
                return "Invalid number. Please try again."
        except ValueError:
            return "Please enter a number corresponding to the reminder."

    if message_lower in [":edit reminder", "edit reminder"]:
        reminders = load_reminders(session_id)
        if not reminders:
            return "You have no reminders to edit."

        session["step"] = "edit_select"
        session["data"] = {}
        lines = []
        for idx, r in enumerate(reminders):
            lines.append(f"{idx + 1}. {r.get('title', '(no title)')} on {r.get('date')} at {r.get('time')}")
        return "Which reminder would you like to edit?\n" + "\n".join(lines)


    # List reminders
    if message_lower == ":reminders":
        reminders = load_reminders(session_id)
        if reminders:
            lines = []
            for r in reminders:
                if not isinstance(r, dict):
                    continue
                status = "✅" if r.get("notified") else "⏰"
                lines.append(f"{status} {r.get('title', '(no title)')} on {r.get('date', '?')} at {r.get('time', '?')} — {r.get('location', '?')}")
            return "Your reminders:\n" + "\n".join(lines)
        else:
            return "You have no reminders."

    # Create reminder
    if message_lower in [":create reminder", "create reminder"]:
        session["step"] = "title"
        session["data"] = {}
        return "What would you like to be reminded of?"

    # Edit reminder - start by selecting which reminder
    
    # Handle creating reminder steps
    if session["step"] == "title":
        session["data"]["title"] = message
        session["step"] = "date"
        return "What date? (Format: YYYY-MM-DD)"

    if session["step"] == "date":
        session["data"]["date"] = message
        session["step"] = "time"
        return "What time? (24-hour format: HH:MM)"

    if session["step"] == "time":
        session["data"]["time"] = message
        session["step"] = "location"
        return "Where?"

    if session["step"] == "location":
        session["data"]["location"] = message
        session["data"]["notified"] = False

        reminder = session["data"]
        reminders = load_reminders(session_id)
        reminders.append(reminder)
        save_reminders(session_id, reminders)

        reminder_sessions.pop(session_id)
        return f"Reminder set: {reminder['title']} on {reminder['date']} at {reminder['time']}, at {reminder['location']}"

    # Handle editing reminder steps
    if session["step"] == "edit_select":
        try:
            index = int(message) - 1
            reminders = load_reminders(session_id)
            if 0 <= index < len(reminders):
                session["data"]["index"] = index
                session["step"] = "edit_field"
                return "What do you want to edit? (title, date, time, location)"
            else:
                return "Invalid number. Please try again."
        except ValueError:
            return "Please enter a number corresponding to the reminder."

    if session["step"] == "edit_field":
        field = message_lower
        if field not in ["title", "date", "time", "location"]:
            return "Invalid field. Choose one of: title, date, time, location."
        session["data"]["field"] = field
        session["step"] = "edit_value"
        return f"What is the new {field}?"

    if session["step"] == "edit_value":
        new_value = message
        data = session["data"]
        reminders = load_reminders(session_id)

        index = data["index"]
        field = data["field"]
        reminders[index][field] = new_value

        # Reset notified if date/time changed
        if field in ["date", "time"]:
            reminders[index]["notified"] = False

        save_reminders(session_id, reminders)
        reminder_sessions.pop(session_id)

        updated = reminders[index]
        return f"Reminder updated: {updated['title']} on {updated['date']} at {updated['time']}, at {updated['location']}"

    # Default help message
    return "Type ':create reminder' to add a reminder, ':reminders' to view your reminders, or ':edit reminder' to edit one."

# Django views
def chat_page(request):
    return render(request, 'clpaapp/chat.html')

@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        session_id = "default"  # or make it dynamic per user
        response = handle_message(session_id, message)
        return JsonResponse({'response': response})

    return JsonResponse({'error': 'Invalid method'}, status=400)
