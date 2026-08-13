from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from hostui import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Авторизация и выход
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Главная страница
    path('', lambda request: redirect('documents_page'), name='home'),
    
    # Основные разделы
    path('workspace/', views.workspace_page, name='workspace'),
    path('chat/', views.chat_page, name='chat_page'),
    path('api/chat/', views.chat_page, name='api_chat'),  # <-- ДОБАВЛЕНА ЭТА СТРОКА
    
    # Раздел документов
    path('documents/', views.documents_page, name='documents_page'),
    path('documents/download/<str:doc_id>/', views.download_document, name='download_document'),
]