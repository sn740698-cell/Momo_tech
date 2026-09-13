from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('health/', views.health_check, name='health_check'),
    path('system/status/', views.system_status, name='system_status'),
    path('status/', views.api_status, name='api_status'),
    
    # Memory endpoints
    path('memory/', views.memory_views, name='memory_views'),
    
    # Hardware & IoT endpoints
    path('devices/', views.device_list, name='device_list'),
    path('devices/<str:device_id>/', views.device_detail, name='device_detail'),
    
    # Local LLM endpoints
    path('ollama/status/', views.ollama_status, name='ollama_status'),
    path('ollama/models/', views.ollama_models, name='ollama_models'),
    path('chat/', views.api_chat, name='api_chat'),
    path('chat/clear/', views.api_chat_clear, name='api_chat_clear'),
    path('message/', views.api_message, name='api_message'),
    
    # Documents & Finance
    path('documents/', views.document_views, name='document_views'),
    path('documents/<str:document_id>/', views.document_detail, name='document_detail'),
    path('finance/<str:document_id>/', views.finance_detail, name='finance_detail'),
    
    # Privacy & Settings
    path('settings/privacy/', views.privacy_settings, name='privacy_settings'),
    
    # Text-to-Speech (TTS) endpoints
    path('tts/', views.api_tts, name='api_tts'),
    path('tts/voices/', views.api_tts_voices, name='api_tts_voices'),

    # Vision & Emotion Perception endpoints
    path('vision/status/', views.vision_status, name='vision_status'),
    path('vision/capture/', views.vision_capture, name='vision_capture'),
    path('vision/stream/', views.vision_stream, name='vision_stream'),
    path('vision/preview/', views.vision_preview, name='vision_preview'),

    # Desktop Automation & Mindful Game Break endpoints
    path('automation/launch_game/', views.automation_launch_game, name='automation_launch_game'),
    path('automation/motivate/', views.automation_motivate, name='automation_motivate'),
    path('automation/games/', views.automation_games_list, name='automation_games_list'),

    # Web Crawler & Real-Time Intelligence endpoints
    path('crawler/crawl/', views.api_crawl_url, name='api_crawl_url'),
    path('crawler/search/', views.api_crawl_search, name='api_crawl_search'),

    # Multi-Agent AI Workflow endpoints
    path('workflow/execute/', views.workflow_execute, name='workflow_execute'),
    path('workflow/executions/', views.workflow_executions_list, name='workflow_executions_list'),
    path('workflow/executions/<str:execution_id>/', views.workflow_execution_detail, name='workflow_execution_detail'),
    path('workflow/sources/', views.workflow_sources, name='workflow_sources'),
    path('workflow/health/', views.workflow_health, name='workflow_health'),
]

