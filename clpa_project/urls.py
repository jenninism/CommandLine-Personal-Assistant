from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('clpaapp.urls')),  # delegate root and /chat/ to clpaapp.urls
]
