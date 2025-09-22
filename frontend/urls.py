from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.project_list, name='project-list'),
    path('projects/<int:project_id>/', views.project_detail, name='project-detail'),
    path('projects/<int:project_id>/commits/', views.project_commits, name='project-commits'),
    path('report/', views.report, name='report'),
    path('report/<int:project_id>/', views.report_detail, name='report-detail'),
    path('export/<int:project_id>/', views.export_report, name='export-report'),
]