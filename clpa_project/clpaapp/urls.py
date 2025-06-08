from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),         # Chat UI page
    path('chat/', views.chatbot_response, name='chat'),  # Chatbot API endpoint
]
