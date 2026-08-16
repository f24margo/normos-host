from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from hostui import views
from hostui import views_research

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', lambda request: redirect('documents_page'), name='home'),

    path('workspace/', views.workspace_page, name='workspace'),
    path('chat/', views.chat_page, name='chat_page'),

    path('api/chat/', views.chat_page, name='api_chat'),
    path('api/analyze/', views.analyze_api, name='analyze_api'),
    path('api/propose_oov/', views.propose_oov_api, name='propose_oov_api'),

    path('documents/', views.documents_page, name='documents_page'),
    path('documents/download/<str:doc_id>/', views.download_document, name='download_document'),

    # NKS-014 Research Console (staff only)
    path('research/', views_research.research_console, name='research_console'),
    path('api/research/status', views_research.research_status_api, name='research_status_api'),
    path('api/research/tests/run', views_research.research_golden_run_api, name='research_golden_run'),
    path('api/research/analyze', views_research.research_analyze_api, name='research_analyze'),
]