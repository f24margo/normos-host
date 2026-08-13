from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from hostui import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Авторизация и выход
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Главная страница (перенаправление на документы)
    path('', lambda request: redirect('documents_page'), name='home'),
    
    # Основные разделы
    path('workspace/', views.workspace_page, name='workspace'),
    path('chat/', views.chat_page, name='chat_page'),
    
    # API эндпоинты
    path('api/chat/', views.chat_page, name='api_chat'),
    path('api/analyze/', views.analyze_api, name='analyze_api'),
    path('api/propose_oov/', views.propose_oov_api, name='propose_oov_api'),
    
    # Раздел документов
    path('documents/', views.documents_page, name='documents_page'),
    path('documents/download/<str:doc_id>/', views.download_document, name='download_document'),
]