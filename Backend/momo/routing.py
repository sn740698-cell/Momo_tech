from django.urls import re_path
from .consumers import MomoConsumer

websocket_urlpatterns = [
    re_path(r"^ws/momo/?$", MomoConsumer.as_asgi()),
]
