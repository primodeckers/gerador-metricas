from django.urls import path
from .views import (
    GitlabTokenView,
    GitlabProjectsView,
    GitlabProjectDetailView,
    GitlabProjectCommitsView,
    GitlabDeveloperStatsView,
    HealthCheckView,
)

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('gitlab/token/', GitlabTokenView.as_view(), name='gitlab-token'),
    path('gitlab/projects/', GitlabProjectsView.as_view(), name='gitlab-projects'),
    path('gitlab/projects/<int:project_id>/', GitlabProjectDetailView.as_view(), name='gitlab-project-detail'),
    path('gitlab/projects/<int:project_id>/commits/', GitlabProjectCommitsView.as_view(), name='gitlab-project-commits'),
    path('gitlab/projects/<int:project_id>/stats/', GitlabDeveloperStatsView.as_view(), name='gitlab-developer-stats'),
]
