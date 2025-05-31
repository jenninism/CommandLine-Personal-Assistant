from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def chat_page(request):
    # Render the chat HTML page
    return render(request, 'clpaapp/chat.html')

@csrf_exempt  # For simplicity, disable CSRF protection here (not for production)
def chatbot_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').lower()

        replies = {
            "hi": "Hello!",
            "hello": "Hi there!",
            "what can you do": "I can answer FAQ questions and open websites.",
            "who are you": "I am your Command Line Personal Assistant.",
            "bye": "Goodbye!",
            "how are you": "I'm just code, but thanks for asking!",
            "yow": "Hi there!"
        }

        url = None
        response = replies.get(message, "Sorry, I don't understand.")

        if message == "open google":
            url = "https://www.google.com"
            response = "Opening Google..."
        elif message == "open youtube":
            url = "https://www.youtube.com"
            response = "Opening YouTube..."

        return JsonResponse({'response': response, 'url': url})
    else:
        return JsonResponse({'error': 'Invalid method'}, status=400)
