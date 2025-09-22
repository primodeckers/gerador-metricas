import gitlab
import datetime
import urllib3
from django.conf import settings
from collections import defaultdict
from .cache_manager import cache_result
from .code_parser import CodeParser
from .performance_config import PERFORMANCE_CONFIG, ESTIMATION_CONFIG
from .timeout_config import TIMEOUT_CONFIG


# Desativar avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações para otimização
MAX_WORKERS = 3  # Reduzido para evitar sobrecarga
MAX_PAGES = 3    # Reduzido para limitar chamadas
PER_PAGE = 50    # Reduzido para respostas mais rápidas

class GitlabClient:
    def __init__(self, token):
        self.token = token
        self.url = settings.GITLAB_API_URL
        self.code_parser = CodeParser()

        self.client = gitlab.Gitlab(
            self.url, 
            private_token=token, 
            ssl_verify=False,  # Desabilitar verificação SSL para acessar o GitLab interno
            per_page=PER_PAGE,   # Aumentar itens por página para reduzir número de chamadas
            timeout=30,  # Timeout de 30 segundos para todas as operações
            retry_transient_errors=True,  # Retry automático para erros temporários
            keep_base_url=True  # Manter a URL base fornecida pelo usuário
        )
        try:
            # Tentar autenticar para garantir que o cliente está funcionando
            self.client.auth()
        except Exception as e:
            # Log do erro mas não falha na inicialização
            pass
    
    def test_connectivity(self):
        """Testa a conectividade com o GitLab"""
        try:
            # Teste simples de conectividade
            user = self.client.user
            if user:
                return True
            else:
                return False
        except Exception as e:
            return False
    
    @cache_result('projects')
    def get_projects(self):
        """Retorna todos os projetos acessíveis pelo token (com cache)"""
        try:
            # Usar os parâmetros originais que funcionavam antes
            projects = self.client.projects.list(
                all=True, 
                order_by='name', 
                sort='asc',
                timeout=TIMEOUT_CONFIG['LIST_PROJECTS_TIMEOUT']
            )
            
            return projects
        except Exception as e:
            raise Exception(f"Erro ao buscar projetos: {str(e)}")
    
    @cache_result('project')
    def get_project(self, project_id):
        """Busca um projeto específico por ID (com cache)"""
        try:
            return self.client.projects.get(project_id)
        except Exception as e:
            raise Exception(f"Erro ao buscar projeto {project_id}: {str(e)}")
    
    def _get_main_branch(self, project):
        """Determina a branch principal do projeto (otimizado)"""
        try:
            # Primeiro tenta obter a branch padrão diretamente do projeto
            if hasattr(project, 'default_branch') and project.default_branch:
                return project.default_branch
                
            # Se não tiver, busca todas as branches
            branches = project.branches.list(all=False, per_page=20)  # Limita para evitar muitas chamadas
            if not branches:

                return None
                
            # Selecionar branch principal (main, master, develop)
            for branch_name in ["main", "master", "develop"]:
                for branch in branches:
                    if branch.name == branch_name:
                        return branch.name
            
            # Se não encontrou os branches padrão, usa o primeiro branch
            return branches[0].name
        except Exception as e:

            return "master"  # Fallback para master
    
    @cache_result('commit_diff')
    def get_commit_diff(self, project, commit_id):
        """Obtém o diff de um commit específico (com cache)"""
        try:
            commit = project.commits.get(commit_id)
            diff = commit.diff(timeout=15)  # Timeout menor para diffs
            return diff
        except Exception as e:
            return None
    
    @cache_result('commits')
    def get_project_commits(self, project_id, since=None, until=None, limit=None, analyze_diffs=True):
        """Busca commits de um projeto em um período específico (otimizado)"""
        try:
            project = self.get_project(project_id)
            
            # Converter datas para string se necessário
            since_str = since.strftime('%Y-%m-%d') if hasattr(since, 'strftime') else since
            until_str = until.strftime('%Y-%m-%d') if hasattr(until, 'strftime') else until
            
            # Buscar branches disponíveis
            branches = project.branches.list(all=True, timeout=20)
            
            # Priorizar branches principais
            branch_principal = None
            preferred_branches = ['main', 'master', 'develop']
            
            for preferred in preferred_branches:
                for branch in branches:
                    if branch.name == preferred:
                        branch_principal = branch
                        break
                if branch_principal:
                    break
            
            # Se não encontrou branch preferencial, usar a primeira disponível
            if branch_principal is None and branches:
                branch_principal = branches[0]

            # Primeira tentativa: sem ref_name (mais abrangente)
            per_page = int(limit) if limit else 50
            commits = []
            total = 0
            
            try:
                commits = project.commits.list(
                    all=True,
                    per_page=per_page,
                    since=since_str,
                    until=until_str,
                    timeout=25  # Timeout reduzido
                )
                total = len(commits)
                
                # Adicionar informação de branch aos commits
                for commit in commits:
                    if not hasattr(commit, 'ref_name'):
                        commit.ref_name = 'multiple'
                    if not hasattr(commit, 'branch_name'):
                        commit.branch_name = 'multiple'
            except Exception as e:
                commits = []
                total = 0

            # Fallback 1: branch preferencial
            if total == 0 and branch_principal is not None:
                try:
                    commits = project.commits.list(
                        ref_name=branch_principal.name,
                        all=True,
                        per_page=per_page,
                        since=since_str,
                        until=until_str,
                        timeout=25
                    )
                    total = len(commits)
                    
                    # Adicionar informação de branch específica aos commits
                    for commit in commits:
                        if not hasattr(commit, 'ref_name'):
                            commit.ref_name = branch_principal.name
                        if not hasattr(commit, 'branch_name'):
                            commit.branch_name = branch_principal.name
                except Exception as e:
                    commits = []
                    total = 0

            # Fallback 2: iterar múltiplas branches
            if total == 0:
                unique_commits = {}
                
                # Separar branches protegidas e não protegidas
                protected_branches = [b for b in branches if getattr(b, 'protected', False)]
                unprotected_branches = [b for b in branches if not getattr(b, 'protected', False)]
                
                # Priorizar branches não protegidas primeiro
                branches_to_try = unprotected_branches + protected_branches
                max_branches = min(3, len(branches_to_try))  # Reduzido para 3 branches
                
                for idx in range(max_branches):
                    b = branches_to_try[idx]
                    try:
                        c = project.commits.list(
                            ref_name=b.name,
                            all=False,
                            per_page=20,  # Reduzido para 20
                            since=since_str,
                            until=until_str,
                            timeout=15  # Timeout reduzido
                        )
                        
                        for item in c:
                            if not hasattr(item, 'ref_name'):
                                item.ref_name = b.name
                            if not hasattr(item, 'branch_name'):
                                item.branch_name = b.name
                            unique_commits[item.id] = item
                            
                        # Se encontrou commits suficientes, parar de buscar
                        if len(unique_commits) >= 30:  # Reduzido para 30
                            break
                            
                    except Exception as be:
                        continue
                
                commits = list(unique_commits.values())
                total = len(commits)

            return commits
        except Exception as e:
            raise Exception(f"Erro ao buscar commits: {str(e)}")
    
    @cache_result('commits_cards')
    def get_project_commits_for_cards(self, project_id, limit=5):
        """Busca commits de um projeto otimizado para exibição em cards"""
        try:
            # Usar configuração específica para cards
            max_commits = PERFORMANCE_CONFIG['MAX_COMMITS_FOR_CARDS']
            actual_limit = min(int(limit) if limit else max_commits, max_commits)
            
            # Buscar commits sem análise de diff (apenas para exibição)
            commits = self.get_project_commits(project_id, limit=actual_limit, analyze_diffs=False)
            
            if not commits:
                return []
            
            # Retornar apenas os dados necessários para os cards
            card_commits = []
            for commit in commits:
                card_commit = {
                    'id': commit.id,
                    'short_id': commit.short_id,
                    'title': commit.title,
                    'author_name': commit.author_name,
                    'author_email': commit.author_email,
                    'authored_date': commit.authored_date,
                    'created_at': getattr(commit, 'created_at', commit.authored_date),
                    'message': commit.message,
                    'ref_name': getattr(commit, 'ref_name', None),
                    'branch_name': getattr(commit, 'branch_name', None)
                }
                card_commits.append(card_commit)
            
            return card_commits
            
        except Exception as e:
            return []
    
    def get_developer_stats(self, project_id, since=None, until=None):
        """Calcula estatísticas de desenvolvedores em um período (otimizado)"""
        
        # Garantir que since e until são strings no formato correto
        try:
            if since and isinstance(since, str):
                since_date = datetime.datetime.strptime(since, '%Y-%m-%d')
                since = since_date.strftime('%Y-%m-%d')
            
            if until and isinstance(until, str):
                until_date = datetime.datetime.strptime(until, '%Y-%m-%d')
                until = until_date.strftime('%Y-%m-%d')
        except ValueError as e:
            # Usar datas padrão em caso de erro
            since = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            until = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Buscar commits com limite otimizado
        max_commits = PERFORMANCE_CONFIG['MAX_COMMITS_PER_REQUEST']
        try:
            commits = self.get_project_commits(project_id, since, until, limit=max_commits)
        except Exception as e:
            return []
        
        if not commits:
            return []
        
        # Inicializa estrutura para armazenar estatísticas
        stats = defaultdict(lambda: {
            'name': '', 
            'email': '', 
            'additions': 0, 
            'deletions': 0, 
            'commits': 0,
            'additions_code': 0,
            'deletions_code': 0,
            'additions_comments': 0,
            'deletions_comments': 0,
            'additions_blank': 0,
            'deletions_blank': 0,
        })
        
        # Processa commits em lotes otimizados
        project = self.get_project(project_id)
        batch_size = PERFORMANCE_CONFIG['BATCH_SIZE']
        
        # Selecionar uma amostra menor de commits para buscar stats detalhados
        max_detailed = PERFORMANCE_CONFIG['MAX_COMMITS_FOR_DETAILED_ANALYSIS']
        sample_size = max(1, min(max_detailed, len(commits) // 10))
        sample_commits = set()
        if len(commits) > 0:
            # Selecionar commits mais recentes para análise detalhada
            for i in range(min(sample_size, len(commits))):
                sample_commits.add(commits[i].id)
        
        # Processar todos os commits, mas com estratégia otimizada
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i + batch_size]
            
            # Processar lote sequencialmente para evitar problemas de concorrência
            for commit in batch:
                try:
                    self._process_commit_stats(project, commit, stats, sample_commits)
                except Exception as e:
                    continue
        
        result = list(stats.values())
        return result
    
    def _process_commit_stats(self, project, commit, stats, sample_commits=None):
        """Processa estatísticas de um commit individual com contagem otimizada"""
        try:
            # Usar apenas informações básicas do commit para evitar timeout
            author_email = getattr(commit, 'author_email', 'unknown@example.com')
            author_name = getattr(commit, 'author_name', 'Unknown')
            
            # Armazena nome e email do autor
            stats[author_email]['name'] = author_name
            stats[author_email]['email'] = author_email
            stats[author_email]['commits'] += 1
            
            # Adicionar informações de branch se disponíveis
            branch_name = getattr(commit, 'branch_name', None)
            ref_name = getattr(commit, 'ref_name', None)
            
            # Inicializar estrutura de branches se não existir
            if 'branches' not in stats[author_email]:
                stats[author_email]['branches'] = {}
            
            # Determinar branch para contagem
            display_branch = branch_name if branch_name else (ref_name if ref_name else 'unknown')
            
            # Inicializar contadores para esta branch se não existir
            if display_branch not in stats[author_email]['branches']:
                stats[author_email]['branches'][display_branch] = {
                    'commits': 0,
                    'additions': 0,
                    'deletions': 0,
                    'additions_code': 0,
                    'deletions_code': 0,
                    'additions_comments': 0,
                    'deletions_comments': 0,
                    'additions_blank': 0,
                    'deletions_blank': 0,
                }
            
            # Incrementar contadores da branch específica
            stats[author_email]['branches'][display_branch]['commits'] += 1
            
            # Inicializar contadores gerais se não existirem
            if 'additions_code' not in stats[author_email]:
                stats[author_email]['additions_code'] = 0
                stats[author_email]['deletions_code'] = 0
                stats[author_email]['additions_comments'] = 0
                stats[author_email]['deletions_comments'] = 0
                stats[author_email]['additions_blank'] = 0
                stats[author_email]['deletions_blank'] = 0
            
            # Estratégia de otimização: usar diff real apenas para commits recentes ou importantes
            use_real_diff = False
            
            # Verificar se deve usar diff real baseado em critérios
            if sample_commits and commit.id in sample_commits:
                use_real_diff = True
            elif hasattr(commit, 'created_at'):
                # Usar diff real apenas para commits dos últimos N dias (configurável)
                try:
                    from datetime import datetime, timedelta
                    recent_days = PERFORMANCE_CONFIG['USE_REAL_DIFF_FOR_RECENT_DAYS']
                    commit_date = datetime.fromisoformat(commit.created_at.replace('Z', '+00:00'))
                    if commit_date > datetime.now() - timedelta(days=recent_days):
                        use_real_diff = True
                except:
                    pass
            
            # Tentar obter diff real apenas se necessário
            if use_real_diff:
                try:
                    diff = self.get_commit_diff(project, commit.id)
                    if diff and len(diff) > 0:
                        # Analisar diff real
                        total_additions = 0
                        total_deletions = 0
                        total_additions_code = 0
                        total_deletions_code = 0
                        total_additions_comments = 0
                        total_deletions_comments = 0
                        total_additions_blank = 0
                        total_deletions_blank = 0
                        
                        for file_diff in diff:
                            filename = file_diff.get('new_path', file_diff.get('old_path', 'unknown'))
                            diff_content = file_diff.get('diff', '')
                            
                            if diff_content:
                                file_stats = self.code_parser.analyze_diff(diff_content, filename)
                                
                                total_additions += file_stats['additions']
                                total_deletions += file_stats['deletions']
                                total_additions_code += file_stats['additions_code']
                                total_deletions_code += file_stats['deletions_code']
                                total_additions_comments += file_stats['additions_comments']
                                total_deletions_comments += file_stats['deletions_comments']
                                total_additions_blank += file_stats['additions_blank']
                                total_deletions_blank += file_stats['deletions_blank']
                        
                        # Usar estatísticas reais se disponíveis
                        if total_additions > 0 or total_deletions > 0:
                            additions = total_additions
                            deletions = total_deletions
                            additions_code = total_additions_code
                            deletions_code = total_deletions_code
                            additions_comments = total_additions_comments
                            deletions_comments = total_deletions_comments
                            additions_blank = total_additions_blank
                            deletions_blank = total_deletions_blank
                        else:
                            # Fallback para estimativa inteligente
                            additions, deletions, additions_code, deletions_code, additions_comments, deletions_comments, additions_blank, deletions_blank = self._estimate_commit_stats(commit)
                    else:
                        # Fallback para estimativa inteligente
                        additions, deletions, additions_code, deletions_code, additions_comments, deletions_comments, additions_blank, deletions_blank = self._estimate_commit_stats(commit)
                except Exception as e:
                    # Fallback para estimativa inteligente
                    additions, deletions, additions_code, deletions_code, additions_comments, deletions_comments, additions_blank, deletions_blank = self._estimate_commit_stats(commit)
            else:
                # Usar estimativa inteligente para commits antigos
                additions, deletions, additions_code, deletions_code, additions_comments, deletions_comments, additions_blank, deletions_blank = self._estimate_commit_stats(commit)
            
            # Adicionar ao total geral
            stats[author_email]['additions'] += additions
            stats[author_email]['deletions'] += deletions
            stats[author_email]['additions_code'] += additions_code
            stats[author_email]['deletions_code'] += deletions_code
            stats[author_email]['additions_comments'] += additions_comments
            stats[author_email]['deletions_comments'] += deletions_comments
            stats[author_email]['additions_blank'] += additions_blank
            stats[author_email]['deletions_blank'] += deletions_blank
            
            # Adicionar à branch específica
            stats[author_email]['branches'][display_branch]['additions'] += additions
            stats[author_email]['branches'][display_branch]['deletions'] += deletions
            stats[author_email]['branches'][display_branch]['additions_code'] += additions_code
            stats[author_email]['branches'][display_branch]['deletions_code'] += deletions_code
            stats[author_email]['branches'][display_branch]['additions_comments'] += additions_comments
            stats[author_email]['branches'][display_branch]['deletions_comments'] += deletions_comments
            stats[author_email]['branches'][display_branch]['additions_blank'] += additions_blank
            stats[author_email]['branches'][display_branch]['deletions_blank'] += deletions_blank
            
        except Exception as e:
            # Se não conseguir obter as estatísticas, continua com o próximo commit
            pass
    
    def _estimate_commit_stats(self, commit):
        """Estima estatísticas de commit baseado em heurísticas inteligentes"""
        commit_message = getattr(commit, 'message', '')
        message_length = len(commit_message)
        
        # Usar configurações de estimativa
        thresholds = ESTIMATION_CONFIG['MESSAGE_THRESHOLDS']
        estimates = ESTIMATION_CONFIG['COMMIT_ESTIMATES']
        
        # Determinar tipo de commit baseado no tamanho da mensagem
        if message_length > thresholds['LARGE_COMMIT']:
            commit_type = 'LARGE'
        elif message_length > thresholds['MEDIUM_COMMIT']:
            commit_type = 'MEDIUM'
        elif message_length > thresholds['SMALL_COMMIT']:
            commit_type = 'SMALL'
        else:
            commit_type = 'TINY'
        
        # Obter estimativas baseadas no tipo
        additions = estimates[commit_type]['additions']
        deletions = estimates[commit_type]['deletions']
        
        # Usar configurações de distribuição
        code_pct = ESTIMATION_CONFIG['CODE_PERCENTAGE']
        comments_pct = ESTIMATION_CONFIG['COMMENTS_PERCENTAGE']
        blank_pct = ESTIMATION_CONFIG['BLANK_PERCENTAGE']
        
        # Calcular distribuição
        additions_code = int(additions * code_pct)
        deletions_code = int(deletions * code_pct)
        additions_comments = int(additions * comments_pct)
        deletions_comments = int(deletions * comments_pct)
        additions_blank = int(additions * blank_pct)
        deletions_blank = int(deletions * blank_pct)
        
        return additions, deletions, additions_code, deletions_code, additions_comments, deletions_comments, additions_blank, deletions_blank