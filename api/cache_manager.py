import time
import logging
from functools import wraps
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Tempos de cache em segundos (otimizados para performance máxima)
CACHE_TIMES = {
    'projects': 7200,   # 2 horas para lista de projetos (dados raramente mudam)
    'project': 3600,    # 1 hora para detalhes de projeto
    'commits': 3600,    # 1 hora para commits (dados históricos)
    'commits_cards': 900, # 15 minutos para commits de cards (mais frequentes)
    'stats': 4800,      # 1.3 horas para estatísticas (cálculos pesados)
    'branches': 1800,   # 30 minutos para branches (podem mudar mais frequentemente)
    'commit_diff': 1800, # 30 minutos para diffs de commits (dados que podem mudar)
}

def cache_result(cache_key_prefix, timeout=None):
    """
    Decorator para cache de resultados de funções.
    
    Args:
        cache_key_prefix: Prefixo para a chave de cache
        timeout: Tempo em segundos para expiração do cache (se None, usa o padrão do tipo)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determina o tipo de dados para definir timeout padrão
            data_type = cache_key_prefix.split('_')[0] if '_' in cache_key_prefix else 'default'
            cache_timeout = timeout or CACHE_TIMES.get(data_type, 300)  # 5 min default
            
            # Constrói a chave de cache com base nos argumentos
            cache_parts = [cache_key_prefix]
            
            # Adiciona argumentos não-self à chave
            if len(args) > 1:  # primeiro arg é self
                cache_parts.extend([str(arg) for arg in args[1:]])
            
            # Adiciona kwargs ordenados à chave
            if kwargs:
                for key in sorted(kwargs.keys()):
                    if kwargs[key] is not None:
                        cache_parts.append(f"{key}:{kwargs[key]}")
            
            cache_key = "_".join(cache_parts)
            
            # Tenta obter do cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Se não estiver em cache, executa a função
            result = func(*args, **kwargs)
            
            # Armazena no cache
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator
