from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('execute-task/', views.execute_task, name='execute_task'),
    path('task-status/<int:task_id>/', views.task_status, name='task_status'),
    path('api/stop-task/<int:task_id>/', views.stop_task, name='stop_task'),
    path('api/live-output/<int:task_id>/', views.get_live_output, name='live_output'),
    path('api/portfolio-performance/', views.get_portfolio_performance, name='portfolio_performance'),
    path('api/recent-signals/', views.get_recent_signals, name='recent_signals'),
    path('api/companies/', views.get_companies_api, name='companies_api'),
    path('api/company/<str:symbol>/', views.get_company_details, name='company_details'),
]
