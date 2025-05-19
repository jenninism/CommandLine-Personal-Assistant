from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),         # serve chat UI at /
    path('chat/', views.chatbot_response, name='chat'),  # API endpoint at /chat/
]
