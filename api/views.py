from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse
from .serializers import (
    GitlabTokenSerializer,
    GitlabProjectSerializer,
    GitlabCommitSerializer,
    DeveloperStatSerializer
)
from .gitlab_client import GitlabClient

class GitlabTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Valida o token do GitLab e armazena na sessão do usuário
        (Mantido para retrocompatibilidade mas usa token fixo)
        """
        # Ignorando o token recebido e usando o fixo
        token = settings.GITLAB_TOKEN
        
        try:
            # Testa a conexão com o GitLab usando o token fixo
            client = GitlabClient(token)
            client.get_projects()
            
            # Armazena o token na sessão
            request.session['gitlab_token'] = token
            
            return Response({"detail": "Token armazenado com sucesso"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GitlabProjectsView(APIView):
    """
    Lista os projetos disponíveis para o token armazenado na sessão
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Usar token da sessão ou token fixo se não existir
        token = request.session.get('gitlab_token', settings.GITLAB_TOKEN)
        
        # Verificar se há parâmetro de busca
        search_query = request.query_params.get('search', '').lower()
        
        try:
            client = GitlabClient(token)
            projects = client.get_projects()
            
            # Serializa apenas os campos que queremos
            serialized_projects = []
            for project in projects:
                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'name_with_namespace': project.name_with_namespace,
                    'description': project.description,
                    'web_url': project.web_url,
                    'last_activity_at': project.last_activity_at,
                    'star_count': getattr(project, 'star_count', 0),
                    'forks_count': getattr(project, 'forks_count', 0),
                    'created_at': project.created_at,
                    'default_branch': getattr(project, 'default_branch', 'main'),
                    'visibility': getattr(project, 'visibility', 'private')
                }
                
                # Filtrar no backend se houver termo de busca
                if search_query:
                    name = str(project_data['name']).lower()
                    namespace = str(project_data['name_with_namespace']).lower()
                    description = str(project_data['description'] or '').lower()
                    
                    if (search_query in name or 
                        search_query in namespace or 
                        search_query in description):
                        serialized_projects.append(project_data)
                else:
                    serialized_projects.append(project_data)
            
            serializer = GitlabProjectSerializer(serialized_projects, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GitlabProjectDetailView(APIView):
    """
    Busca detalhes de um projeto específico
    """
    permission_classes = [AllowAny]
    
    def get(self, request, project_id):
        # Usar token da sessão ou token fixo se não existir
        token = request.session.get('gitlab_token', settings.GITLAB_TOKEN)
        
        try:
            client = GitlabClient(token)
            project = client.get_project(project_id)
            
            # Serializa apenas os campos que queremos
            project_data = {
                'id': project.id,
                'name': project.name,
                'name_with_namespace': project.name_with_namespace,
                'description': project.description,
                'web_url': project.web_url,
                'last_activity_at': project.last_activity_at,
                'created_at': project.created_at,
                'default_branch': project.default_branch,
                'visibility': project.visibility,
                'path': project.path,
                'path_with_namespace': project.path_with_namespace
            }
            
            return Response(project_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GitlabProjectCommitsView(APIView):
    """
    Busca os commits de um projeto específico
    """
    permission_classes = [AllowAny]
    
    def get(self, request, project_id):
        # Usar token da sessão ou token fixo se não existir
        token = request.session.get('gitlab_token', settings.GITLAB_TOKEN)
        
        # Obter parâmetros de data (aceita tanto start_date/end_date quanto since/until)
        since = request.query_params.get('since')
        until = request.query_params.get('until')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = request.query_params.get('limit')
        
        # Usar since/until se fornecidos, caso contrário usar start_date/end_date
        if not since and start_date:
            since = start_date
        if not until and end_date:
            until = end_date
        
        # Se há limite, não aplicar filtros de data (busca os últimos commits independente da data)
        if limit:
            since = None
            until = None
        else:
            # Se não foram fornecidas datas, usa o último mês
            if not since:
                since = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not until:
                until = timezone.now().strftime('%Y-%m-%d')
            

        
        try:
            client = GitlabClient(token)
            
            # Se há limite pequeno (para cards), usar método otimizado
            if limit and int(limit) <= 10:
                commits = client.get_project_commits_for_cards(project_id, limit=limit)
                # Commits já vêm serializados do método otimizado
                return Response(commits)
            else:
                # Para requisições maiores, usar método completo
                commits = client.get_project_commits(project_id, since=since, until=until, limit=limit)
                
                # Serializa apenas os campos que queremos
                serialized_commits = []
                for commit in commits:
                    commit_data = {
                        'id': commit.id,
                        'short_id': commit.short_id,
                        'title': commit.title,
                        'author_name': commit.author_name,
                        'author_email': commit.author_email,
                        'authored_date': commit.authored_date,
                        'created_at': getattr(commit, 'created_at', commit.authored_date),  # Usar created_at se disponível, senão authored_date
                        'message': commit.message,
                        'ref_name': getattr(commit, 'ref_name', None),
                        'branch_name': getattr(commit, 'branch_name', None)
                    }
                    serialized_commits.append(commit_data)
                
                serializer = GitlabCommitSerializer(serialized_commits, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GitlabDeveloperStatsView(APIView):
    """
    Busca as estatísticas de desenvolvimento por autor
    """
    permission_classes = [AllowAny]
    
    def get(self, request, project_id):
        # Usar token da sessão ou token fixo se não existir
        token = request.session.get('gitlab_token', settings.GITLAB_TOKEN)
        
        # Obter parâmetros de data (aceita tanto start_date/end_date quanto since/until)
        since = request.query_params.get('since')
        until = request.query_params.get('until')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Verificar se deve limpar cache
        clear_cache = request.query_params.get('clear_cache', 'false').lower() == 'true'
        
        # Usar since/until se fornecidos, caso contrário usar start_date/end_date
        if not since and start_date:
            since = start_date
        if not until and end_date:
            until = end_date
        
        # Se não especificado, usa o último mês
        if not since:
            since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not until:
            until = datetime.now().strftime('%Y-%m-%d')
        
        # Garantir que as datas estão no formato correto
        try:
            if since and isinstance(since, str):
                since_date = datetime.strptime(since, '%Y-%m-%d')
                since = since_date.strftime('%Y-%m-%d')
            
            if until and isinstance(until, str):
                until_date = datetime.strptime(until, '%Y-%m-%d')
                until = until_date.strftime('%Y-%m-%d')
        except ValueError:
            # Usar datas padrão em caso de erro
            since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            until = datetime.now().strftime('%Y-%m-%d')
        
        # Limpar cache se solicitado
        if clear_cache:
            from django.core.cache import cache
            # Limpar cache relacionado ao projeto específico
            cache_keys_to_clear = [
                f'projects_{project_id}',
                f'project_{project_id}',
                f'commits_{project_id}',
                f'stats_{project_id}',
            ]
            for key in cache_keys_to_clear:
                cache.delete(key)
            # Também limpar chaves com parâmetros de data
            for key in cache_keys_to_clear:
                cache.delete(f"{key}_since:{since}_until:{until}")
        
        try:
            client = GitlabClient(token)
            
            stats = client.get_developer_stats(project_id, since=since, until=until)
            
            serializer = DeveloperStatSerializer(stats, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckView(APIView):
    """
    Endpoint de health check para monitoramento do container
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Retorna o status da aplicação
        """
        try:
            # Verificar se o banco de dados está acessível
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return JsonResponse({
                "status": "healthy",
                "timestamp": timezone.now().isoformat(),
                "database": "connected",
                "version": "1.0.0"
            })
        except Exception as e:
            return JsonResponse({
                "status": "unhealthy",
                "timestamp": timezone.now().isoformat(),
                "error": str(e)
            }, status=500)