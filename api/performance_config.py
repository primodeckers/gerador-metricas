"""
Configurações de performance para o GitLab Client
"""

# Configurações de otimização
PERFORMANCE_CONFIG = {
    # Limites de commits
    'MAX_COMMITS_PER_REQUEST': 10,  # Máximo de commits por requisição (reduzido para cards)
    'MAX_COMMITS_FOR_DETAILED_ANALYSIS': 3,  # Máximo de commits para análise detalhada
    'MAX_COMMITS_FOR_CARDS': 5,  # Máximo de commits para exibição em cards
    
    # Configurações de cache
    'CACHE_TIMEOUT_COMMIT_DIFF': 1800,  # 30 minutos para diffs
    'CACHE_TIMEOUT_STATS': 3600,  # 1 hora para estatísticas
    
    # Configurações de processamento
    'BATCH_SIZE': 5,  # Tamanho do lote para processamento
    'MAX_WORKERS': 2,  # Máximo de workers para processamento paralelo
    
    # Configurações de fallback
    'USE_REAL_DIFF_FOR_RECENT_DAYS': 30,  # Usar diff real apenas para commits dos últimos 30 dias
    'FALLBACK_SAMPLE_PERCENTAGE': 0.1,  # 10% dos commits para análise detalhada
    
    # Configurações de timeout
    'API_TIMEOUT': 30,  # Timeout para chamadas da API
    'DIFF_TIMEOUT': 15,  # Timeout específico para diffs
}

# Configurações de estimativa inteligente
ESTIMATION_CONFIG = {
    # Distribuição típica de linhas em commits
    'CODE_PERCENTAGE': 0.75,  # 75% código
    'COMMENTS_PERCENTAGE': 0.15,  # 15% comentários
    'BLANK_PERCENTAGE': 0.10,  # 10% linhas em branco
    
    # Heurísticas baseadas no tamanho da mensagem
    'MESSAGE_THRESHOLDS': {
        'LARGE_COMMIT': 200,  # Commits grandes
        'MEDIUM_COMMIT': 100,  # Commits médios
        'SMALL_COMMIT': 50,   # Commits pequenos
    },
    
    # Estimativas de linhas por tipo de commit
    'COMMIT_ESTIMATES': {
        'LARGE': {'additions': 50, 'deletions': 25},
        'MEDIUM': {'additions': 25, 'deletions': 12},
        'SMALL': {'additions': 15, 'deletions': 8},
        'TINY': {'additions': 8, 'deletions': 4},
    }
}

