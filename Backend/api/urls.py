from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('status/', views.api_status, name='api_status'),
    path('message/', views.api_message, name='api_message'),
    path('ollama/status/', views.api_ollama_status, name='api_ollama_status'),
    path('chat/', views.api_chat, name='api_chat'),
]
