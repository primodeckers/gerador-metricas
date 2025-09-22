import json
import csv
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib import messages
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from django.conf import settings
import os

# Configurar sessão de requests otimizada
def get_requests_session():
    """Retorna uma sessão de requests otimizada com pool de conexões"""
    session = requests.Session()
    
    # Configurar retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # Configurar adapter com pool de conexões
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_api_url(request, path):
    """Helper to build API URL"""
    return f"{request.scheme}://{request.get_host()}/api/{path}"

def read_sidebar_template():
    """Lê o template do menu lateral"""
    template_path = os.path.join(settings.BASE_DIR, 'templates', 'sidebar_base.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    return template

def insert_content_into_sidebar_template(content, title="Gerador de Métricas GitLab"):
    """Insere o conteúdo no template de menu lateral"""
    template = read_sidebar_template()
    
    # Substituir o título
    template = template.replace('<title>Gerador de Métricas GitLab</title>', f'<title>{title}</title>')
    
    # JavaScript com efeitos visuais elegantes para todos os botões
    action_buttons_js = """
    <script>
    // Função global para criar loading overlay com progresso
    function createLoadingOverlay(message = 'Processando dados...', subMessage = 'Aguarde, isso pode levar alguns segundos') {
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <p>${message}</p>
                <small class="text-muted">${subMessage}</small>
                <div class="loading-progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
        `;
        document.body.appendChild(loadingOverlay);
        
        // Iniciar animação de progresso
        const progressBar = loadingOverlay.querySelector('.progress-bar');
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15; // Progresso aleatório mas crescente
            if (progress > 90) progress = 90; // Não completar até a requisição terminar
            progressBar.style.width = progress + '%';
        }, 200);
        
        // Armazenar interval para limpeza
        loadingOverlay.progressInterval = progressInterval;
        
        return loadingOverlay;
    }
    
    // Função para detectar requisições AJAX
    function setupAjaxDetection(loadingOverlay, element) {
        let activeRequests = 0;
        let pageLoaded = false;
        
        const removeLoading = () => {
            if (!pageLoaded) {
                pageLoaded = true;
                removeLoadingOverlay(loadingOverlay);
                if (element) element.classList.remove('loading');
            }
        };
        
        // Interceptar requisições XMLHttpRequest
        const originalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            const originalSend = xhr.send;
            
            xhr.open = function(method, url, async, user, password) {
                if (async !== false) {
                    activeRequests++;
                }
                return originalOpen.apply(this, arguments);
            };
            
            xhr.send = function(data) {
                const result = originalSend.apply(this, arguments);
                
                xhr.addEventListener('loadend', function() {
                    activeRequests--;
                    if (activeRequests === 0) {
                        setTimeout(removeLoading, 200); // Pequeno delay para garantir que a página atualizou
                    }
                });
                
                return result;
            };
            
            return xhr;
        };
        
        // Interceptar requisições fetch
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            activeRequests++;
            return originalFetch.apply(this, args).finally(() => {
                activeRequests--;
                if (activeRequests === 0) {
                    setTimeout(removeLoading, 200);
                }
            });
        };
        
        // Timeout de segurança
        setTimeout(() => {
            if (!pageLoaded) {
                removeLoading();
            }
        }, 3000);
        
        return { removeLoading };
    }
    
    // Função global para remover loading
    function removeLoadingOverlay(loadingOverlay) {
        if (loadingOverlay && loadingOverlay.parentNode) {
            // Completar a barra de progresso antes de remover
            const progressBar = loadingOverlay.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.style.transition = 'width 0.3s ease';
            }
            
            // Limpar interval de progresso
            if (loadingOverlay.progressInterval) {
                clearInterval(loadingOverlay.progressInterval);
            }
            
            // Aguardar um pouco para mostrar o progresso completo
            setTimeout(() => {
            loadingOverlay.parentNode.removeChild(loadingOverlay);
            }, 300);
        }
    }
    
    // Função para detectar carregamento da página com melhor sincronização
    function setupPageLoadDetection(loadingOverlay, element) {
        let pageLoaded = false;
        let startTime = Date.now();
        
        const removeLoading = () => {
            if (!pageLoaded) {
                pageLoaded = true;
                removeLoadingOverlay(loadingOverlay);
                if (element) element.classList.remove('loading');
            }
        };
        
        // Detectar quando a página realmente carregou
        const checkPageLoad = () => {
            // Verificar se todos os recursos carregaram
            if (document.readyState === 'complete' && 
                document.images && 
                Array.from(document.images).every(img => img.complete)) {
                removeLoading();
            }
        };
        
        // Detectar mudança de página (para navegação)
        const checkNavigation = () => {
            // Se a URL mudou, significa que a navegação aconteceu
            if (window.location.href !== window.lastUrl) {
                window.lastUrl = window.location.href;
                // Aguardar um pouco para o conteúdo carregar
                setTimeout(removeLoading, 500);
            }
        };
        
        // Múltiplas formas de detectar carregamento
        window.addEventListener('load', checkPageLoad);
        document.addEventListener('DOMContentLoaded', checkPageLoad);
        window.addEventListener('popstate', checkNavigation);
        
        // Verificar periodicamente se a página carregou
        const intervalCheck = setInterval(() => {
            if (pageLoaded) {
                clearInterval(intervalCheck);
                return;
            }
            
            const elapsed = Date.now() - startTime;
            
            // Se passou muito tempo, remover loading
            if (elapsed > 5000) { // Reduzido de 10s para 5s
                removeLoading();
                clearInterval(intervalCheck);
            }
            
            // Verificar se a página carregou
            checkPageLoad();
        }, 100); // Verificar a cada 100ms
        
        // Timeout de segurança mais agressivo
        const safetyTimeout = setTimeout(() => {
            removeLoading();
            clearInterval(intervalCheck);
        }, 3000); // Reduzido de 10s para 3s
        
        return { checkPageLoad, safetyTimeout, intervalCheck };
    }
    
    // Função específica para detecção de navegação com sincronização de API
    function setupNavigationDetection(loadingOverlay, element) {
        let pageLoaded = false;
        let startTime = Date.now();
        let urlChanged = false;
        let activeApiRequests = 0;
        let apiRequestsCompleted = false;
        
        const removeLoading = () => {
            if (!pageLoaded) {
                pageLoaded = true;
                // Limpar observer
                if (observer) {
                    observer.disconnect();
                }
                removeLoadingOverlay(loadingOverlay);
                if (element) element.classList.remove('loading');
            }
        };
        
        // Detectar mudança de URL
        const checkUrlChange = () => {
            if (window.location.href !== window.lastUrl) {
                urlChanged = true;
                window.lastUrl = window.location.href;
            }
        };
        
        // Interceptar requisições específicas da API do sistema
        const interceptApiRequests = () => {
            // Interceptar XMLHttpRequest
            const originalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {
                const xhr = new originalXHR();
                const originalOpen = xhr.open;
                const originalSend = xhr.send;
                
                xhr.open = function(method, url, async, user, password) {
                    // Só contar requisições para a API do sistema
                    if (url.includes('/api/') || url.includes('gitlab')) {
                        activeApiRequests++;
                    }
                    return originalOpen.apply(this, arguments);
                };
                
                xhr.send = function(data) {
                    const result = originalSend.apply(this, arguments);
                    
                    xhr.addEventListener('loadend', function() {
                        if (xhr.responseURL.includes('/api/') || xhr.responseURL.includes('gitlab')) {
                            activeApiRequests--;
                            
                            // Se todas as requisições da API terminaram
                            if (activeApiRequests === 0) {
                                apiRequestsCompleted = true;
                            }
                        }
                    });
                    
                    return result;
                };
                
                return xhr;
            };
            
            // Interceptar fetch
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                if (typeof url === 'string' && (url.includes('/api/') || url.includes('gitlab'))) {
                    activeApiRequests++;
                    
                    return originalFetch.apply(this, args).finally(() => {
                        activeApiRequests--;
                        
                        if (activeApiRequests === 0) {
                            apiRequestsCompleted = true;
                        }
                    });
                }
                
                return originalFetch.apply(this, args);
            };
        };
        
        // Verificar se a página carregou completamente
        const checkPageLoad = () => {
            if (document.readyState === 'complete' && 
                document.images && 
                Array.from(document.images).every(img => img.complete) &&
                urlChanged) {
                
                // Verificar se há conteúdo na página (não está vazia)
                const hasContent = document.querySelector('.container-fluid, .main-content, .card, table, .row');
                if (hasContent) {
                    // Aguardar um pouco mais para garantir que o conteúdo carregou
                    setTimeout(removeLoading, 1200);
                } else {
                    // Se não há conteúdo, aguardar mais
                    setTimeout(() => checkPageLoad(), 500);
                }
            }
        };
        
        // Armazenar URL atual
        window.lastUrl = window.location.href;
        
        // Interceptar requisições da API
        interceptApiRequests();
        
        // Observar mudanças no DOM para detectar quando o conteúdo realmente mudou
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // Verificar se foram adicionados elementos de conteúdo
                    const addedContent = Array.from(mutation.addedNodes).some(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            return node.querySelector && (
                                node.querySelector('table tbody tr') ||
                                node.querySelector('.card-body') ||
                                node.querySelector('.alert') ||
                                node.querySelector('.jumbotron')
                            );
                        }
                        return false;
                    });
                    
                    if (addedContent && apiRequestsCompleted) {
                        setTimeout(removeLoading, 500);
                    }
                }
            });
        });
        
        // Função para verificar se o conteúdo da página mudou
        const checkContentChange = () => {
            const hasTableData = document.querySelector('table tbody tr:not(.skeleton)');
            const hasCards = document.querySelector('.card:not(.loading)');
            const hasJumbotron = document.querySelector('.jumbotron');
            const hasProjectCards = document.querySelector('.card .card-body .btn[href*="projects"]');
            const hasProjectList = document.querySelector('.card-header h5:contains("Lista de Projetos")');
            
            // Verificar se há conteúdo real (não apenas estrutura vazia)
            const hasRealContent = (hasTableData || hasCards || hasJumbotron || hasProjectCards) && 
                                 document.querySelector('.container-fluid')?.innerHTML.length > 1000;
            
            if (hasRealContent && apiRequestsCompleted) {
                setTimeout(removeLoading, 1000); // 1 segundo adicional
                return true;
            }
            return false;
        };
        
        // Observar mudanças no body
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Múltiplas formas de detectar carregamento
        window.addEventListener('load', checkPageLoad);
        document.addEventListener('DOMContentLoaded', checkPageLoad);
        window.addEventListener('popstate', checkUrlChange);
        
        // Verificar periodicamente se a página carregou
        const intervalCheck = setInterval(() => {
            if (pageLoaded) {
                clearInterval(intervalCheck);
                return;
            }
            
            const elapsed = Date.now() - startTime;
            
            // Verificar mudança de URL
            checkUrlChange();
            
            
            // Verificar se há dados carregados na página E se as requisições da API terminaram
            if (urlChanged && (apiRequestsCompleted || elapsed > 3000)) { // 3 segundos mínimo
                // Verificar se há conteúdo real na página
                if (checkContentChange()) {
                    clearInterval(intervalCheck);
                    return;
                }
            }
            
            // Se passou muito tempo, remover loading
            if (elapsed > 12000) { // 12 segundos para navegação
                removeLoading();
                clearInterval(intervalCheck);
            }
            
            // Verificar se a página carregou
            checkPageLoad();
        }, 500); // Verificar a cada 500ms
        
        // Timeout de segurança mais longo para navegação
        const safetyTimeout = setTimeout(() => {
            removeLoading();
            clearInterval(intervalCheck);
        }, 10000); // 10 segundos para navegação
        
        return { checkPageLoad, safetyTimeout, intervalCheck };
    }
    
    // Função específica para detecção de relatórios com gráficos
    function setupReportDetection(loadingOverlay, element) {
        let pageLoaded = false;
        let startTime = Date.now();
        let urlChanged = false;
        let activeApiRequests = 0;
        let apiRequestsCompleted = false;
        let chartsRendered = false;
        
        // Evitar múltiplas instâncias
        if (window.reportDetectionActive) {
            return;
        }
        window.reportDetectionActive = true;
        
        const removeLoading = () => {
            if (!pageLoaded) {
                pageLoaded = true;
                window.reportDetectionActive = false; // Limpar flag
                
                // Limpar observers e timeouts
                domObserver.disconnect();
                clearTimeout(domChangeTimeout);
                
                removeLoadingOverlay(loadingOverlay);
                if (element) element.classList.remove('loading');
            }
        };
        
        // Detectar mudança de URL
        const checkUrlChange = () => {
            if (window.location.href !== window.lastUrl) {
                urlChanged = true;
                window.lastUrl = window.location.href;
            }
        };
        
        // Interceptar requisições específicas da API do sistema
        const interceptApiRequests = () => {
            // Interceptar XMLHttpRequest
            const originalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {
                const xhr = new originalXHR();
                const originalOpen = xhr.open;
                const originalSend = xhr.send;
                
                xhr.open = function(method, url, async, user, password) {
                    // Só contar requisições para a API do sistema
                    if (url.includes('/api/') || url.includes('gitlab')) {
                        activeApiRequests++;
                        
                        // Adicionar parâmetro clear_cache=true para requisições de stats
                        if (url.includes('/stats/') && !url.includes('clear_cache=')) {
                            const separator = url.includes('?') ? '&' : '?';
                            url = url + separator + 'clear_cache=true';
                        }
                    }
                    return originalOpen.apply(this, arguments);
                };
                
                xhr.send = function(data) {
                    const result = originalSend.apply(this, arguments);
                    
                    xhr.addEventListener('loadend', function() {
                        if (xhr.responseURL.includes('/api/') || xhr.responseURL.includes('gitlab')) {
                            activeApiRequests--;
                            
                            // Se todas as requisições da API terminaram
                            if (activeApiRequests === 0) {
                                apiRequestsCompleted = true;
                                lastApiCompletionTime = Date.now();
                            }
                        }
                    });
                    
                    return result;
                };
                
                return xhr;
            };
            
            // Interceptar fetch
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                let url = args[0];
                if (typeof url === 'string' && (url.includes('/api/') || url.includes('gitlab'))) {
                    // Adicionar parâmetro clear_cache=true para requisições de stats
                    if (url.includes('/stats/') && !url.includes('clear_cache=')) {
                        const separator = url.includes('?') ? '&' : '?';
                        url = url + separator + 'clear_cache=true';
                        args[0] = url;
                    }
                    
                    activeApiRequests++;
                    
                    return originalFetch.apply(this, args).finally(() => {
                        activeApiRequests--;
                        
                        if (activeApiRequests === 0) {
                            apiRequestsCompleted = true;
                            lastApiCompletionTime = Date.now();
                        }
                    });
                }
                
                return originalFetch.apply(this, args);
            };
        };
        
        // Verificar se os gráficos foram renderizados
        const checkChartsRendered = () => {
            const additionsChart = document.querySelector('#additionsChart');
            const deletionsChart = document.querySelector('#deletionsChart');
            const commitsChart = document.querySelector('#commitsChart');
            
            if (additionsChart && deletionsChart && commitsChart) {
                // Verificar se os canvas têm dimensões válidas
                const hasValidDimensions = additionsChart.width > 0 && additionsChart.height > 0 &&
                                         deletionsChart.width > 0 && deletionsChart.height > 0 &&
                                         commitsChart.width > 0 && commitsChart.height > 0;
                
                if (!hasValidDimensions) {
                    return false;
                }
                
                // Verificar se os canvas têm conteúdo (gráficos renderizados)
                try {
                    const additionsCtx = additionsChart.getContext('2d');
                    const deletionsCtx = deletionsChart.getContext('2d');
                    const commitsCtx = commitsChart.getContext('2d');
                    
                    // Verificar se os gráficos foram desenhados (não estão vazios)
                    const additionsData = additionsCtx.getImageData(0, 0, additionsChart.width, additionsChart.height).data;
                    const deletionsData = deletionsCtx.getImageData(0, 0, deletionsChart.width, deletionsChart.height).data;
                    const commitsData = commitsCtx.getImageData(0, 0, commitsChart.width, commitsChart.height).data;
                    
                    const hasAdditionsData = additionsData.some(pixel => pixel !== 0);
                    const hasDeletionsData = deletionsData.some(pixel => pixel !== 0);
                    const hasCommitsData = commitsData.some(pixel => pixel !== 0);
                    
                    // Todos os gráficos devem ter dados
                    if (hasAdditionsData && hasDeletionsData && hasCommitsData) {
                        chartsRendered = true;
                        return true;
                    }
                } catch (error) {
                    // Erro ao verificar gráficos
                }
            }
            return false;
        };
        
        // Verificar se Chart.js está carregado
        const checkChartJsLoaded = () => {
            return typeof Chart !== 'undefined' && Chart.Chart;
        };
        
        // Verificar se há dados na tabela
        const checkTableData = () => {
            const tableRows = document.querySelectorAll('table tbody tr:not(.skeleton)');
            const hasRealTableData = tableRows.length > 0;
            
            // Verificar se há conteúdo real na página (não apenas estrutura vazia)
            const container = document.querySelector('.container-fluid');
            const hasRealContent = container && container.innerHTML.length > 2000;
            
            // Verificar se há dados reais nas linhas da tabela (não apenas estrutura vazia)
            const hasRealTableContent = Array.from(tableRows).some(row => {
                const cells = row.querySelectorAll('td');
                return cells.length > 0 && Array.from(cells).some(cell => cell.textContent.trim().length > 0);
            });
            
            
            return hasRealTableData && hasRealContent && hasRealTableContent;
        };
        
        // Função para verificar se o relatório carregou completamente
        const checkReportLoad = () => {
            if (document.readyState === 'complete' && 
                document.images && 
                Array.from(document.images).every(img => img.complete) &&
                urlChanged) {
                
                // Verificar se há dados na tabela
                const hasTableData = checkTableData();
                
                if (hasTableData) {
                    // Aguardar um pouco mais para os gráficos carregarem
                    setTimeout(() => {
                        const chartsReady = checkChartsRendered();
                        const chartJsLoaded = checkChartJsLoaded();
                        
                        
                        if (chartsReady || (chartJsLoaded && apiRequestsCompleted)) {
                            setTimeout(removeLoading, 2000); // 2 segundos adicional para garantir que tudo carregou
                        }
                    }, 2000); // Aguardar 2s para os gráficos renderizarem
                } else {
                    // Se não há dados, aguardar mais
                    setTimeout(() => checkReportLoad(), 500);
                }
            }
        };
        
        // Função para verificar se a página HTML foi completamente renderizada
        const checkPageFullyRendered = () => {
            return new Promise((resolve) => {
                // Verificar se o DOM está completamente carregado
                if (document.readyState !== 'complete') {
                    resolve(false);
                    return;
                }
                
                // Verificar se todas as imagens carregaram
                const images = Array.from(document.images);
                if (!images.every(img => img.complete)) {
                    resolve(false);
                    return;
                }
                
                // Verificar se não há elementos com loading/skeleton
                const loadingElements = document.querySelectorAll('.loading, .skeleton, [class*="loading"], [class*="skeleton"]');
                if (loadingElements.length > 0) {
                    resolve(false);
                    return;
                }
                
                // Verificar se há conteúdo real na página
                const container = document.querySelector('.container-fluid');
                if (!container || container.innerHTML.length < 2000) {
                    resolve(false);
                    return;
                }
                
                // Verificar se todos os scripts carregaram (incluindo Chart.js)
                if (typeof Chart === 'undefined') {
                    resolve(false);
                    return;
                }
                
                // Verificar se há elementos de gráfico na página
                const chartElements = document.querySelectorAll('#additionsChart, #deletionsChart, #commitsChart');
                if (chartElements.length === 0) {
                    resolve(false);
                    return;
                }
                
                // Verificar se há dados na tabela
                const tableRows = document.querySelectorAll('table tbody tr:not(.skeleton)');
                if (tableRows.length === 0) {
                    resolve(false);
                    return;
                }
                
                // Verificar se há dados reais nas células da tabela
                const hasRealData = Array.from(tableRows).some(row => {
                    const cells = row.querySelectorAll('td');
                    return cells.length > 0 && Array.from(cells).some(cell => {
                        const text = cell.textContent.trim();
                        return text.length > 0 && !text.includes('Loading') && !text.includes('...');
                    });
                });
                
                if (!hasRealData) {
                    resolve(false);
                    return;
                }
                
                // Verificar se os gráficos foram realmente renderizados
                const chartsRendered = checkChartsRendered();
                if (!chartsRendered) {
                    resolve(false);
                    return;
                }
                
                // Verificar se não há requisições pendentes
                if (activeApiRequests > 0) {
                    resolve(false);
                    return;
                }
                
                // Aguardar múltiplos frames para garantir que tudo foi renderizado
                let frameCount = 0;
                const checkFrames = () => {
                    frameCount++;
                    if (frameCount >= 8) { // Aguardar 8 frames para ser mais rigoroso
                        resolve(true);
                    } else {
                        requestAnimationFrame(checkFrames);
                    }
                };
                
                requestAnimationFrame(checkFrames);
            });
        };
        
        // Armazenar URL atual
        window.lastUrl = window.location.href;
        
        // Interceptar requisições da API
        interceptApiRequests();
        
        // Observar mudanças no DOM para detectar quando parou de renderizar
        let domChangeTimeout;
        let lastContentHash = '';
        let contentStableCount = 0;
        let isContentStable = false;
        const domObserver = new MutationObserver((mutations) => {
            // Resetar timeout quando há mudanças
            clearTimeout(domChangeTimeout);
            contentStableCount = 0;
            isContentStable = false;
            
            // Verificar se houve mudanças significativas no conteúdo
            const currentContent = document.querySelector('.container-fluid')?.innerHTML || '';
            const currentHash = currentContent.length.toString();
            
            if (currentHash !== lastContentHash) {
                lastContentHash = currentHash;
            }
            
            // Se não há mudanças por 4 segundos, considerar que parou de renderizar
            domChangeTimeout = setTimeout(() => {
                contentStableCount++;
                
                // Só considerar estável após 3 verificações consecutivas
                if (contentStableCount >= 3) {
                    isContentStable = true;
                }
            }, 4000);
        });
        
        // Observar mudanças no body
        domObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true
        });
        
        // Múltiplas formas de detectar carregamento
        window.addEventListener('load', checkReportLoad);
        document.addEventListener('DOMContentLoaded', checkReportLoad);
        window.addEventListener('popstate', checkUrlChange);
        
        // Variáveis para monitorar mudanças de conteúdo
        let lastContentSnapshot = '';
        let contentUpdateCount = 0;
        let lastApiCompletionTime = 0;
        
        // Função para verificar se o conteúdo realmente mudou
        const checkContentUpdate = () => {
            const currentContent = document.querySelector('.container-fluid')?.innerHTML || '';
            const currentSnapshot = currentContent.substring(0, 1000); // Primeiros 1000 caracteres
            
            if (currentSnapshot !== lastContentSnapshot) {
                lastContentSnapshot = currentSnapshot;
                contentUpdateCount++;
                
                // Verificar se há dados reais na tabela após a atualização
                const tableRows = document.querySelectorAll('table tbody tr:not(.skeleton)');
                const hasRealData = Array.from(tableRows).some(row => {
                    const cells = row.querySelectorAll('td');
                    return cells.length > 0 && Array.from(cells).some(cell => {
                        const text = cell.textContent.trim();
                        return text.length > 0 && !text.includes('Loading') && !text.includes('...') && !text.includes('0');
                    });
                });
                
                return hasRealData;
            }
            return false;
        };
        
        // Verificar periodicamente se o relatório carregou
        const intervalCheck = setInterval(async () => {
            if (pageLoaded) {
                clearInterval(intervalCheck);
                return;
            }
            
            const elapsed = Date.now() - startTime;
            
            // Verificar mudança de URL
            checkUrlChange();
            
            // Só verificar se a URL mudou
            if (urlChanged) {
                const hasTableData = checkTableData();
                const chartsReady = checkChartsRendered();
                const chartJsLoaded = checkChartJsLoaded();
                const contentUpdated = checkContentUpdate();
                
                // Verificar se há dados na tabela (mínimo 3 segundos)
                const hasMinimumTime = elapsed > 3000;
                
                
                // PRIORIDADE 1: Aguardar requisições da API completarem
                if (activeApiRequests > 0) {
                    // Se passou muito tempo com requisições ativas, pode ser um problema
                    if (elapsed > 20000) {
                        apiRequestsCompleted = true;
                    }
                    return; // Não prosseguir enquanto há requisições ativas
                }
                
                // PRIORIDADE 2: Aguardar tempo mínimo e dados da tabela
                if (!hasMinimumTime || !hasTableData) {
                    return; // Não prosseguir sem tempo mínimo e dados
                }
                
                // PRIORIDADE 3: Aguardar Chart.js carregar
                if (!chartJsLoaded) {
                    return; // Não prosseguir sem Chart.js
                }
                
                // PRIORIDADE 4: Aguardar conteúdo ser atualizado após API
                if (apiRequestsCompleted) {
                    const timeSinceApiCompletion = elapsed - lastApiCompletionTime;
                    
                    if (timeSinceApiCompletion < 5000) { // 5 segundos após API completar
                        return; // Aguardar conteúdo ser atualizado
                    }
                    
                    // Se não houve atualização de conteúdo recente, aguardar mais
                    if (!contentUpdated && timeSinceApiCompletion < 10000) {
                        return;
                    }
                }
                
                // PRIORIDADE 5: Aguardar gráficos renderizar
                if (!chartsReady) {
                    // Se passou muito tempo esperando gráficos, prosseguir mesmo assim
                    if (elapsed > 15000) {
                        // Prosseguir mesmo sem gráficos
                    } else {
                        return; // Aguardar gráficos renderizar
                    }
                }
                
                // PRIORIDADE 6: Verificar se a página foi completamente renderizada
                const isFullyRendered = await checkPageFullyRendered();
                
                if (isFullyRendered) {
                    // Verificar se o conteúdo está estável
                    if (!isContentStable) {
                        return;
                    }
                    
                    // Aguardar mais 3 segundos para garantir renderização completa
                    setTimeout(() => {
                        // Verificar novamente se ainda está renderizado e estável
                        const finalCheck = checkPageFullyRendered();
                        if (finalCheck && isContentStable) {
                            removeLoading();
                            clearInterval(intervalCheck);
                        }
                    }, 3000);
                    return;
                }
            }
            
            // Se passou muito tempo, remover loading
            if (elapsed > 30000) { // 30 segundos para relatórios
                window.reportDetectionActive = false; // Limpar flag
                removeLoading();
                clearInterval(intervalCheck);
            }
            
            // Verificar se o relatório carregou
            checkReportLoad();
        }, 500); // Verificar a cada 500ms para ser mais responsivo
        
        // Timeout de segurança para relatórios
        const safetyTimeout = setTimeout(() => {
            removeLoading();
            clearInterval(intervalCheck);
        }, 12000); // 12 segundos para relatórios
        
        return { checkReportLoad, safetyTimeout, intervalCheck };
    }
    
    document.addEventListener('DOMContentLoaded', function() {
        // 1. Loading para formulários de filtro
        const filterForms = document.querySelectorAll('form[id*="filter"], form[action*="report"]');
        filterForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                this.classList.add('loading');
                
                // Verificar se é o formulário de filtro de datas em relatórios
                if (this.id === 'date-filter-form' || this.action.includes('/report/')) {
                    const loadingOverlay = createLoadingOverlay('Filtrando dados...', 'Aplicando filtro de período...');
                    setupReportDetection(loadingOverlay, this);
                } else {
                const loadingOverlay = createLoadingOverlay('Processando dados...', 'Aguarde, isso pode levar alguns segundos');
                    setupAjaxDetection(loadingOverlay, this);
                }
            });
        });
        
        // 2. Loading para links de navegação do menu principal (EXCLUINDO botões de voltar e modo escuro)
        const navLinks = document.querySelectorAll('.sidebar .nav-link, .navbar .nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // Verificar se é um link interno (excluindo voltar e modo escuro)
                if (this.href && !this.href.includes('javascript:') && !this.target &&
                    !this.textContent.toLowerCase().includes('voltar') &&
                    !this.textContent.toLowerCase().includes('back') &&
                    !this.textContent.toLowerCase().includes('modo escuro') &&
                    !this.textContent.toLowerCase().includes('dark mode') &&
                    !this.onclick) {
                    this.classList.add('loading');
                    
                    let message = 'Navegando...';
                    let subMessage = 'Aguarde enquanto carregamos os dados...';
                    
                    if (this.textContent.includes('Início')) {
                        message = 'Carregando página inicial...';
                        subMessage = 'Preparando dashboard...';
                    } else if (this.textContent.includes('Projetos')) {
                        message = 'Carregando lista de projetos...';
                        subMessage = 'Buscando projetos no GitLab...';
                    } else if (this.textContent.includes('Relatórios')) {
                        message = 'Carregando relatórios...';
                        subMessage = 'Preparando interface de relatórios...';
                    }
                    
                    const loadingOverlay = createLoadingOverlay(message, subMessage);
                    setupNavigationDetection(loadingOverlay, this);
                }
            });
        });
        
        // 3. Loading para botões de ação (exportação, detalhes, etc.) - EXCLUINDO botões de voltar
        const actionButtons = document.querySelectorAll('a.btn:not(.nav-link):not([href*="voltar"]):not([href*="back"]), button[type="submit"]');
        actionButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Verificar se é um link ou botão de ação (excluindo voltar)
                if (this.href && !this.href.includes('javascript:') && 
                    !this.textContent.toLowerCase().includes('voltar') &&
                    !this.textContent.toLowerCase().includes('back')) {
                    this.classList.add('loading');
                    
                    let message = 'Processando...';
                    let subMessage = 'Aguarde...';
                    
                    if (this.href.includes('export')) {
                        message = 'Exportando dados...';
                        subMessage = 'Preparando arquivo para download...';
                    } else if (this.href.includes('report')) {
                        message = 'Gerando relatório...';
                        subMessage = 'Analisando dados do projeto...';
                    } else if (this.href.includes('projects')) {
                        message = 'Carregando projeto...';
                        subMessage = 'Buscando informações...';
                    }
                    
                    const loadingOverlay = createLoadingOverlay(message, subMessage);
                    
                    // Se for um link de relatório, usar detecção específica para gráficos
                    if (this.href.includes('report') && this.href.includes('/report/')) {
                        setupReportDetection(loadingOverlay, this);
                    } else if (this.href.includes('/projects/') || this.href.includes('/report/')) {
                        // Links de navegação principal (projetos, relatórios) usam detecção de navegação
                        setupNavigationDetection(loadingOverlay, this);
                    } else {
                    setupPageLoadDetection(loadingOverlay, this);
                    }
                }
            });
        });
        
        // 4. Loading para botões de paginação
        const paginationLinks = document.querySelectorAll('.pagination .page-link');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                if (!this.classList.contains('disabled')) {
                    this.classList.add('loading');
                    const loadingOverlay = createLoadingOverlay('Carregando página...', 'Buscando dados...');
                    setupPageLoadDetection(loadingOverlay, this);
                }
            });
        });
        
        // 5. Efeito de hover suave em todos os botões e links
        const interactiveElements = document.querySelectorAll('button, .btn, .nav-link, .page-link');
        interactiveElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                if (!this.classList.contains('loading')) {
                    this.style.transform = 'translateY(-2px)';
                    this.style.transition = 'all 0.3s ease';
                }
            });
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
        
        // 6. Loading para botões de busca
        const searchButtons = document.querySelectorAll('button[type="submit"]');
        searchButtons.forEach(button => {
            const form = button.closest('form');
            if (form && form.querySelector('input[name="search"]')) {
                button.addEventListener('click', function(e) {
                    this.classList.add('loading');
                    const loadingOverlay = createLoadingOverlay('Buscando...', 'Filtrando resultados...');
                    setupPageLoadDetection(loadingOverlay, this);
                });
            }
        });
    });
    </script>
    
    <style>
    /* Loading overlay elegante e moderno */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(0, 123, 255, 0.1), rgba(40, 167, 69, 0.1));
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        animation: fadeIn 0.3s ease;
    }
    
    .loading-content {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        padding: 3rem 2.5rem;
        border-radius: 20px;
        text-align: center;
        box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.1),
            0 0 0 1px rgba(255, 255, 255, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        animation: slideInScale 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
        overflow: hidden;
    }
    
    .loading-content::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        animation: shimmer 2s infinite;
    }
    
    .loading-spinner {
        position: relative;
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
    }
    
    .loading-spinner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 4px solid #e9ecef;
        border-top: 4px solid #007bff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    .loading-spinner::after {
        content: '';
        position: absolute;
        top: 8px;
        left: 8px;
        width: calc(100% - 16px);
        height: calc(100% - 16px);
        border: 3px solid transparent;
        border-top: 3px solid #28a745;
        border-radius: 50%;
        animation: spin 1.5s linear infinite reverse;
    }
    
    .loading-dots {
        display: flex;
        justify-content: center;
        margin-bottom: 1.5rem;
        gap: 8px;
    }
    
    .loading-dots span {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: linear-gradient(45deg, #007bff, #28a745);
        animation: pulseBounce 1.4s ease-in-out infinite both;
        box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
    }
    
    .loading-dots span:nth-child(1) { 
        animation-delay: -0.32s; 
        background: linear-gradient(45deg, #007bff, #0056b3);
    }
    .loading-dots span:nth-child(2) { 
        animation-delay: -0.16s; 
        background: linear-gradient(45deg, #28a745, #1e7e34);
    }
    .loading-dots span:nth-child(3) { 
        animation-delay: 0s; 
        background: linear-gradient(45deg, #ffc107, #e0a800);
    }
    
    .loading-content p {
        font-size: 1.1rem;
        font-weight: 600;
        color: #495057;
        margin-bottom: 0.5rem;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    .loading-content small {
        color: #6c757d;
        font-size: 0.9rem;
    }
    
    .loading-progress {
        width: 100%;
        height: 4px;
        background: #e9ecef;
        border-radius: 2px;
        margin-top: 1rem;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #007bff, #28a745);
        border-radius: 2px;
        width: 0%;
        transition: width 0.3s ease;
        position: relative;
    }
    
    .progress-bar::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        animation: progressShimmer 1.5s infinite;
    }
    
    @keyframes progressShimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes pulseBounce {
        0%, 80%, 100% {
            transform: scale(0.8) translateY(0);
            opacity: 0.7;
        }
        40% {
            transform: scale(1.2) translateY(-10px);
            opacity: 1;
        }
    }
    
    @keyframes slideInScale {
        from {
            opacity: 0;
            transform: translateY(-30px) scale(0.9);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    /* Efeito de loading em todos os elementos */
    .loading {
        opacity: 0.8;
        pointer-events: none;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        transform: scale(0.98);
    }
    
    .loading::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        animation: shimmer 1.5s infinite;
        border-radius: inherit;
    }
    
    /* Efeito de pulse em botões durante loading */
    .loading button,
    .loading.btn,
    .loading.nav-link,
    .loading.page-link {
        animation: pulseGlow 2s ease-in-out infinite;
        position: relative;
        overflow: hidden;
    }
    
    /* Efeito especial para links de navegação */
    .sidebar .nav-link.loading {
        background: linear-gradient(135deg, #007bff, #0056b3, #004085);
        color: white !important;
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(0, 123, 255, 0.4);
    }
    
    /* Efeito especial para botões de ação */
    .btn.loading {
        background: linear-gradient(135deg, #28a745, #1e7e34, #155724);
        color: white !important;
        transform: scale(1.01);
        box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
    }
    
    /* Efeito especial para paginação */
    .pagination .page-link.loading {
        background: linear-gradient(135deg, #6c757d, #495057, #343a40);
        color: white !important;
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(108, 117, 125, 0.4);
    }
    
    /* Efeito especial para botões de busca */
    .btn[type="submit"].loading {
        background: linear-gradient(135deg, #17a2b8, #138496, #0c5460);
        color: white !important;
        transform: scale(1.01);
        box-shadow: 0 6px 20px rgba(23, 162, 184, 0.4);
    }
    
    @keyframes pulseGlow {
        0% {
            box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.6);
            transform: scale(0.98);
        }
        50% {
            box-shadow: 0 0 0 8px rgba(0, 123, 255, 0.2);
            transform: scale(1.01);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(0, 123, 255, 0);
            transform: scale(0.98);
        }
    }
    
    /* Skeleton loading moderno para tabelas */
    .skeleton {
        background: linear-gradient(90deg, 
            rgba(240, 240, 240, 0.8) 25%, 
            rgba(220, 220, 220, 0.9) 50%, 
            rgba(240, 240, 240, 0.8) 75%);
        background-size: 200% 100%;
        animation: skeletonWave 2s ease-in-out infinite;
        border-radius: 8px;
        position: relative;
        overflow: hidden;
    }
    
    .skeleton::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, 
            transparent, 
            rgba(255, 255, 255, 0.6), 
            transparent);
        animation: skeletonShimmer 1.5s infinite;
    }
    
    @keyframes skeletonWave {
        0% {
            background-position: 200% 0;
            opacity: 0.8;
        }
        50% {
            opacity: 1;
        }
        100% {
            background-position: -200% 0;
            opacity: 0.8;
        }
    }
    
    @keyframes skeletonShimmer {
        0% {
            left: -100%;
        }
        100% {
            left: 100%;
        }
    }
    
    .skeleton-row {
        height: 24px;
        margin: 12px 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .skeleton-cell {
        height: 18px;
        margin: 6px 0;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Loading states para cards */
    .card.loading {
        opacity: 0.7;
        transform: scale(0.98);
        transition: all 0.3s ease;
    }
    
    .card.loading .card-body {
        position: relative;
        overflow: hidden;
    }
    
    .card.loading .card-body::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, 
            transparent, 
            rgba(255, 255, 255, 0.4), 
            transparent);
        animation: cardShimmer 2s infinite;
    }
    
    @keyframes cardShimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    </style>
    """
    
    # Inserir o JavaScript antes do fechamento do body
    template = template.replace('</body>', action_buttons_js + '</body>')
    
    # Substituir o conteúdo
    old_content = '    <div class="main-content">\n      <!-- Content goes here -->\n      <div class="container-fluid">\n        <h1>Conteúdo da Página</h1>\n        <p>Este é um exemplo de layout com menu lateral.</p>\n      </div>\n    </div>'
    new_content = f'    <div class="main-content">\n      <div class="container-fluid">\n        {content}\n      </div>\n    </div>'
    
    template = template.replace(old_content, new_content)
    
    return template

def generate_recent_projects_html(recent_projects):
    """Gera o HTML para os cards de projetos recentes"""
    if not recent_projects:
        return """
        <div class="col-12">
            <div class="text-center py-4">
                <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                <p class="text-muted">Nenhum projeto encontrado.</p>
            </div>
        </div>
        """
    
    html = ""
    for project in recent_projects:
        # Formatar data da última atividade
        last_activity = project.get('last_activity_at', '')
        if last_activity:
            try:
                from datetime import datetime
                last_activity_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                last_activity_formatted = last_activity_dt.strftime('%d/%m/%Y %H:%M')
            except:
                last_activity_formatted = last_activity[:10]
        else:
            last_activity_formatted = 'N/A'
        
        # Verificar se commits foram carregados com sucesso
        commits_loaded = project.get('commits_loaded', False)
        commits_error = project.get('commits_error', '')
        
        # Gerar HTML dos commits recentes
        commits_html = ""
        if commits_loaded and project.get('recent_commits'):
            for commit in project['recent_commits']:
                commit_author = commit.get('author_name', 'Desconhecido')
                commit_message = commit.get('message', 'Sem mensagem')[:50]
                if len(commit.get('message', '')) > 50:
                    commit_message += '...'
                commit_branch = commit.get('branch_name', 'main')
                commit_date = commit.get('created_at', '')[:10] if commit.get('created_at') else 'N/A'
                
                commits_html += f"""
                <div class="commit-item mb-2 p-2 border rounded" style="background: rgba(248, 249, 250, 0.5);">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <small class="fw-bold text-primary">{commit_author}</small>
                            <div class="text-muted small">{commit_message}</div>
                            <div class="d-flex align-items-center mt-1">
                                <i class="fas fa-code-branch me-1 text-info"></i>
                                <small class="text-muted me-3">{commit_branch}</small>
                                <i class="fas fa-calendar me-1 text-muted"></i>
                                <small class="text-muted">{commit_date}</small>
                            </div>
                        </div>
                    </div>
                </div>
                """
        elif commits_error and 'timeout' in commits_error.lower():
            commits_html = """
            <div class="text-center py-2">
                <i class="fas fa-clock text-warning me-2"></i>
                <small class="text-muted">Carregando commits...</small>
                <div class="spinner-border spinner-border-sm text-primary mt-2" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            </div>
            """
        elif commits_error and 'assíncrono' in commits_error.lower():
            # Mostrar loading para carregamento assíncrono (caso inicial)
            commits_html = """
            <div class="text-center py-2">
                <i class="fas fa-clock text-warning me-2"></i>
                <small class="text-muted">Carregando commits...</small>
                <div class="spinner-border spinner-border-sm text-primary mt-2" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            </div>
            """
        else:
            commits_html = """
            <div class="text-center py-2">
                <small class="text-muted">Nenhum commit recente</small>
            </div>
            """
        
        html += f"""
        <div class="col-md-6 col-lg-3 mb-4">
            <div class="card h-100 shadow-sm project-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0 text-truncate" title="{project.get('name', 'Projeto sem nome')}">
                        <i class="fas fa-project-diagram me-2 text-primary"></i>
                        {project.get('name', 'Projeto sem nome')}
                    </h6>
                    <a href="/projects/{project['id']}/" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>
                            Última atividade: {last_activity_formatted}
                        </small>
                    </div>
                    
                    <div class="commits-section">
                        <h6 class="text-muted mb-2">
                            <i class="fas fa-code-branch me-1"></i>
                            Commits Recentes
                        </h6>
                        <div class="commits-list" style="max-height: 200px; overflow-y: auto;">
                            {commits_html}
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="fas fa-star me-1"></i>
                            {project.get('star_count', 0)} stars
                        </small>
                        <small class="text-muted">
                            <i class="fas fa-code-fork me-1"></i>
                            {project.get('forks_count', 0)} forks
                        </small>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return html

def home(request):
    """Página inicial - Ultra otimizada para performance com fallback robusto"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Busca os projetos para mostrar os recentes (com fallback robusto)
    recent_projects = []
    
    try:
        api_url = get_api_url(request, 'gitlab/projects/')
        session = get_requests_session()
        response = session.get(
            api_url,
            cookies=request.COOKIES,
            timeout=15  # Aumentado para 15 segundos
        )
        
        if response.status_code == 200:
            projects = response.json()
            projects.sort(key=lambda x: x.get('last_activity_at', ''), reverse=True)
            recent_projects = projects[:4]
            
    except requests.exceptions.Timeout:
        try:
            response = requests.get(
                api_url,
                cookies=request.COOKIES,
                timeout=3
            )
            if response.status_code == 200:
                projects = response.json()
                projects.sort(key=lambda x: x.get('last_activity_at', ''), reverse=True)
                recent_projects = projects[:4]
        except Exception:
            pass
            
    except Exception:
        pass
    
    # Commits carregados via AJAX para evitar timeouts
    for project in recent_projects:
        project['recent_commits'] = []
        project['commits_loaded'] = False
        project['commits_error'] = 'Carregamento assíncrono'
    
    # Conteúdo da página inicial
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="jumbotron bg-primary text-white rounded p-5 mb-4">
                    <h1 class="display-4">Gerador de Métricas GitLab</h1>
                    <p class="lead">Sistema para análise e geração de relatórios de contribuições dos desenvolvedores em projetos GitLab.</p>
                    <hr class="my-4">
                    <p>Visualize estatísticas detalhadas, exporte dados e acompanhe a produtividade da sua equipe.</p>
                </div>
            </div>
        </div>
        
        <!-- Projetos Recentes -->
        <div class="row mb-4">
            <div class="col-12">
                <h3 class="mb-3">
                    <i class="fas fa-clock me-2 text-primary"></i>
                    Projetos Recentementes alterados
                </h3>
            </div>
        </div>
        
        <div class="row mb-4" id="recent-projects-container">
            {generate_recent_projects_html(recent_projects)}
        </div>
        
        <!-- JavaScript otimizado para carregar projetos e commits de forma assíncrona -->
        <script>
        // Debounce para evitar muitas chamadas
        function debounce(func, wait) {{
            let timeout;
            return function executedFunction(...args) {{
                const later = () => {{
                    clearTimeout(timeout);
                    func(...args);
                }};
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            }};
        }}
        
        // Intersection Observer para lazy loading
        const observerOptions = {{
            root: null,
            rootMargin: '50px',
            threshold: 0.1
        }};
        
        document.addEventListener('DOMContentLoaded', function() {{
            // Verificar se há projetos carregados
            const projectCards = document.querySelectorAll('.project-card');
            const projectsContainer = document.getElementById('recent-projects-container');
            
            // Se não há projetos, carregar via AJAX
            if (projectCards.length === 0) {{
                console.log('Nenhum projeto encontrado, carregando via AJAX...');
                
                // Mostrar loading
                projectsContainer.innerHTML = `
                    <div class="col-12">
                        <div class="text-center py-4">
                            <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                                <span class="visually-hidden">Carregando...</span>
                            </div>
                            <h5 class="text-muted mb-2">Carregando projetos...</h5>
                            <p class="text-muted">Buscando os projetos mais recentes do GitLab</p>
                        </div>
                    </div>
                `;
                
                // Carregar projetos via AJAX
                fetch('/api/gitlab/projects/', {{
                    method: 'GET',
                    headers: {{
                        'X-Requested-With': 'XMLHttpRequest'
                    }}
                }})
                .then(response => {{
                    if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
                    return response.json();
                }})
                .then(projects => {{
                    console.log(`Carregados ${{projects.length}} projetos via AJAX`);
                    
                    // Ordenar por última atividade e pegar os 4 mais recentes
                    projects.sort((a, b) => new Date(b.last_activity_at || 0) - new Date(a.last_activity_at || 0));
                    const recentProjects = projects.slice(0, 4);
                    
                    if (recentProjects.length > 0) {{
                        // Gerar HTML dos projetos
                        let projectsHtml = '';
                        recentProjects.forEach(project => {{
                            const lastActivity = project.last_activity_at ? new Date(project.last_activity_at).toLocaleDateString('pt-BR') : 'N/A';
                            
                            projectsHtml += `
                                <div class="col-md-6 col-lg-3 mb-4">
                                    <div class="card h-100 shadow-sm project-card">
                                        <div class="card-header d-flex justify-content-between align-items-center">
                                            <h6 class="mb-0 text-truncate" title="${{project.name}}">
                                                <i class="fas fa-project-diagram me-2 text-primary"></i>
                                                ${{project.name}}
                                            </h6>
                                            <a href="/projects/${{project.id}}/" class="btn btn-sm btn-outline-primary">
                                                <i class="fas fa-external-link-alt"></i>
                                            </a>
                                        </div>
                                        <div class="card-body">
                                            <div class="mb-3">
                                                <small class="text-muted">
                                                    <i class="fas fa-clock me-1"></i>
                                                    Última atividade: ${{lastActivity}}
                                                </small>
                                            </div>
                                            
                                            <div class="commits-section">
                                                <h6 class="text-muted mb-2">
                                                    <i class="fas fa-code-branch me-1"></i>
                                                    Commits Recentes
                                                </h6>
                                                <div class="commits-list" style="max-height: 200px; overflow-y: auto;">
                                                    <div class="text-center py-2">
                                                        <i class="fas fa-clock text-warning me-2"></i>
                                                        <small class="text-muted">Carregando commits...</small>
                                                        <div class="spinner-border spinner-border-sm text-primary mt-2" role="status">
                                                            <span class="visually-hidden">Carregando...</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="card-footer">
                                            <div class="d-flex justify-content-between align-items-center">
                                                <small class="text-muted">
                                                    <i class="fas fa-star me-1"></i>
                                                    ${{project.star_count || 0}} stars
                                                </small>
                                                <small class="text-muted">
                                                    <i class="fas fa-code-fork me-1"></i>
                                                    ${{project.forks_count || 0}} forks
                                                </small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }});
                        
                        projectsContainer.innerHTML = projectsHtml;
                        
                        // Agora carregar commits para cada projeto
                        loadCommitsForProjects();
                    }} else {{
                        projectsContainer.innerHTML = `
                            <div class="col-12">
                                <div class="text-center py-4">
                                    <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                                    <p class="text-muted">Nenhum projeto encontrado.</p>
                                </div>
                            </div>
                        `;
                    }}
                }})
                .catch(error => {{
                    console.error('Erro ao carregar projetos:', error);
                    projectsContainer.innerHTML = `
                        <div class="col-12">
                            <div class="text-center py-4">
                                <i class="fas fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                                <h5 class="text-muted mb-2">Erro ao carregar projetos</h5>
                                <p class="text-muted">Tente recarregar a página</p>
                            </div>
                        </div>
                    `;
                }});
            }} else {{
                // Se já há projetos, apenas carregar commits
                loadCommitsForProjects();
            }}
            
            function loadCommitsForProjects() {{
                // Carregar commits dos projetos recentes de forma assíncrona
                const projectCards = document.querySelectorAll('.project-card');
                
                projectCards.forEach((card, index) => {{
                const projectId = card.querySelector('a[href*="/projects/"]')?.href?.match(/\/projects\/(\d+)\//)?.[1];
                if (projectId) {{
                    // Adicionar indicador de loading
                    const commitsSection = card.querySelector('.commits-list');
                    if (commitsSection) {{
                        commitsSection.innerHTML = `
                            <div class="text-center py-2">
                                <i class="fas fa-clock text-warning me-2"></i>
                                <small class="text-muted">Carregando commits...</small>
                                <div class="spinner-border spinner-border-sm text-primary mt-2" role="status">
                                    <span class="visually-hidden">Carregando...</span>
                                </div>
                            </div>
                        `;
                    }}
                    
                    // Carregar commits com timeout curto - limitado aos 5 últimos commits
                    fetch(`/api/gitlab/projects/${{projectId}}/commits/?limit=5`, {{
                        method: 'GET',
                        headers: {{
                            'X-Requested-With': 'XMLHttpRequest'
                        }}
                    }})
                    .then(response => {{
                        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
                        return response.json();
                    }})
                    .then(commits => {{
                        if (commitsSection) {{
                            if (commits && commits.length > 0) {{
                                let commitsHtml = '';
                                commits.forEach(commit => {{
                                    const commitAuthor = commit.author_name || 'Desconhecido';
                                    const commitMessage = commit.message ? (commit.message.length > 50 ? commit.message.substring(0, 50) + '...' : commit.message) : 'Sem mensagem';
                                    const commitBranch = commit.branch_name || 'main';
                                    const commitDate = commit.created_at ? commit.created_at.substring(0, 10) : 'N/A';
                                    
                                    commitsHtml += `
                                        <div class="commit-item mb-2 p-2 border rounded" style="background: rgba(248, 249, 250, 0.5);">
                                            <div class="d-flex justify-content-between align-items-start">
                                                <div class="flex-grow-1">
                                                    <small class="fw-bold text-primary">${{commitAuthor}}</small>
                                                    <div class="text-muted small">${{commitMessage}}</div>
                                                    <div class="d-flex align-items-center mt-1">
                                                        <i class="fas fa-code-branch me-1 text-info"></i>
                                                        <small class="text-muted me-3">${{commitBranch}}</small>
                                                        <i class="fas fa-calendar me-1 text-muted"></i>
                                                        <small class="text-muted">${{commitDate}}</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    `;
                                }});
                                commitsSection.innerHTML = commitsHtml;
                            }} else {{
                                commitsSection.innerHTML = `
                                    <div class="text-center py-2">
                                        <small class="text-muted">Nenhum commit recente</small>
                                    </div>
                                `;
                            }}
                        }}
                    }})
                    .catch(error => {{
                        console.warn(`Erro ao carregar commits do projeto ${{projectId}}:`, error);
                        if (commitsSection) {{
                            commitsSection.innerHTML = `
                                <div class="text-center py-2">
                                    <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                                    <small class="text-muted">Erro ao carregar commits</small>
                                </div>
                            `;
                        }}
                    }});
                }}
            }});
            }}
        }});
        </script>
        
        <div class="row justify-content-center">
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-project-diagram fa-3x text-primary mb-3"></i>
                        <h5 class="card-title">Projetos</h5>
                        <p class="card-text">Visualize todos os projetos disponíveis no GitLab e suas informações básicas.</p>
                        <a href="/projects/" class="btn btn-primary">
                            <i class="fas fa-list me-2"></i> Listar Projetos
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-bar fa-3x text-success mb-3"></i>
                        <h5 class="card-title">Relatórios</h5>
                        <p class="card-text">Gere relatórios detalhados de contribuições por desenvolvedor e período.</p>
                        <a href="/report/" class="btn btn-success">
                            <i class="fas fa-file-alt me-2"></i> Gerar Relatório
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-download fa-3x text-info mb-3"></i>
                        <h5 class="card-title">Exportação</h5>
                        <p class="card-text">Exporte dados em formatos CSV e JSON para análise externa.</p>
                        <a href="/report/" class="btn btn-info">
                            <i class="fas fa-download me-2"></i> Exportar Dados
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border: 1px solid #dee2e6;">
                    <div class="card-header border-0" style="background: rgba(108, 117, 125, 0.1);">
                        <h5 class="mb-0 text-dark">
                            <i class="fas fa-info-circle me-2 text-info"></i>
                            Como usar o sistema
                        </h5>
                    </div>
                    <div class="card-body text-dark">
                        <div class="row">
                            <div class="col-md-6 mb-4">
                                <div class="d-flex align-items-start">
                                    <div class="flex-shrink-0 me-3">
                                        <div class="rounded-circle d-flex align-items-center justify-content-center" 
                                             style="width: 50px; height: 50px; background: linear-gradient(45deg, #6c757d, #495057);">
                                            <i class="fas fa-eye text-white fs-5"></i>
                                        </div>
                                    </div>
                                    <div class="flex-grow-1">
                                        <h6 class="mb-2 text-dark fw-bold">1. Visualizar Projetos</h6>
                                        <p class="mb-0 text-muted">Acesse a lista de projetos para ver todos os repositórios disponíveis no GitLab.</p>
                                    </div>
                                </div>
                                
                                <div class="d-flex align-items-start mt-4">
                                    <div class="flex-shrink-0 me-3">
                                        <div class="rounded-circle d-flex align-items-center justify-content-center" 
                                             style="width: 50px; height: 50px; background: linear-gradient(45deg, #6c757d, #495057);">
                                            <i class="fas fa-chart-line text-white fs-5"></i>
                                        </div>
                                    </div>
                                    <div class="flex-grow-1">
                                        <h6 class="mb-2 text-dark fw-bold">2. Gerar Relatórios</h6>
                                        <p class="mb-0 text-muted">Selecione um projeto e período para gerar relatórios detalhados de contribuições.</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6 mb-4">
                                <div class="d-flex align-items-start">
                                    <div class="flex-shrink-0 me-3">
                                        <div class="rounded-circle d-flex align-items-center justify-content-center" 
                                             style="width: 50px; height: 50px; background: linear-gradient(45deg, #6c757d, #495057);">
                                            <i class="fas fa-filter text-white fs-5"></i>
                                        </div>
                                    </div>
                                    <div class="flex-grow-1">
                                        <h6 class="mb-2 text-dark fw-bold">3. Filtrar por Período</h6>
                                        <p class="mb-0 text-muted">Use os filtros de data para analisar contribuições em períodos específicos.</p>
                                    </div>
                                </div>
                                
                                <div class="d-flex align-items-start mt-4">
                                    <div class="flex-shrink-0 me-3">
                                        <div class="rounded-circle d-flex align-items-center justify-content-center" 
                                             style="width: 50px; height: 50px; background: linear-gradient(45deg, #6c757d, #495057);">
                                            <i class="fas fa-download text-white fs-5"></i>
                                        </div>
                                    </div>
                                    <div class="flex-grow-1">
                                        <h6 class="mb-2 text-dark fw-bold">4. Exportar Dados</h6>
                                        <p class="mb-0 text-muted">Baixe os dados em formato CSV ou JSON para análise externa.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Linha decorativa -->
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="text-center">
                                    <div class="d-inline-block px-4 py-2 rounded-pill" 
                                         style="background: rgba(108, 117, 125, 0.1); border: 1px solid #dee2e6;">
                                        <i class="fas fa-check-circle text-success me-2"></i>
                                        <span class="text-dark fw-bold">Sistema Intuitivo e Fácil de Usar</span>
                                        <i class="fas fa-check-circle text-success ms-2"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, "Início - Gerador de Métricas GitLab")
    
    return HttpResponse(html)

def project_list(request):
    """Lista todos os projetos"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Obter termo de busca e página atual
    search_query = request.GET.get('search', '')
    page = int(request.GET.get('page', '1'))
    per_page = 20  # Número de projetos por página
    
    # Busca os projetos via API interna
    response = requests.get(
        get_api_url(request, 'gitlab/projects/'),
        cookies=request.COOKIES,
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar projetos')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar projetos (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('home')
    
    # Obter todos os projetos
    try:
        projects = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('home')
    
    # Filtrar projetos manualmente (mais simples e garantido)
    if search_query and search_query.strip():
        search_term = search_query.lower().strip()
        filtered_projects = []
        
        for project in projects:
            name = str(project.get('name', '')).lower()
            namespace = str(project.get('name_with_namespace', '')).lower()
            
            if search_term in name or search_term in namespace:
                filtered_projects.append(project)
    else:
        filtered_projects = projects
    
    # Calcular paginação
    total_projects = len(filtered_projects)
    total_pages = (total_projects + per_page - 1) // per_page  # Arredonda para cima
    
    # Ajustar página atual se estiver fora dos limites
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calcular índices de início e fim para a página atual
    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, total_projects)
    
    # Obter projetos da página atual
    current_page_projects = filtered_projects[start_index:end_index]
    
    # Conteúdo da página
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1 class="mb-0">Projetos GitLab <span class="badge bg-primary">{len(filtered_projects)}</span> encontrados</h1>
                    <a href="/" class="btn btn-outline-secondary" onclick="history.back(); return false;">
                        <i class="fas fa-arrow-left me-2"></i> Voltar
                    </a>
                </div>
            </div>
        </div>

        <!-- Campo de busca -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <form method="get" class="row g-3">
                            <div class="col-md-10">
                                <div class="input-group">
                                    <span class="input-group-text"><i class="fas fa-search"></i></span>
                                    <input type="text" name="search" class="form-control" placeholder="Buscar projeto por nome..." value="{search_query}">
                                </div>
                            </div>
                            <div class="col-md-2">
                                <button type="submit" class="btn btn-primary w-100" id="searchButton">
                                    <i class="fas fa-search me-2"></i> Buscar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">Lista de Projetos</h5>
                            <span class="text-muted">{len(filtered_projects)} projetos {f'encontrados para "{search_query}"' if search_query else 'encontrados'}</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Nome</th>
                                        <th>Caminho</th>
                                        <th>Descrição</th>
                                        <th>Última Atividade</th>
                                        <th>Ações</th>
                                    </tr>
                                </thead>
                                <tbody>
    """
    
    # Adiciona linhas da tabela dinamicamente
    if current_page_projects:
        for project in current_page_projects:
            description = project.get('description', '') or 'Sem descrição'
            if len(description) > 100:
                description = description[:100] + '...'
            
            last_activity = project.get('last_activity_at', 'N/A')
            if last_activity and last_activity != 'N/A':
                last_activity = last_activity[:10]
            
            content += f"""
                                    <tr>
                                        <td>
                                            <strong>{project.get('name', '')}</strong>
                                        </td>
                                        <td>{project.get('name_with_namespace', '')}</td>
                                        <td>{description}</td>
                                        <td>{last_activity}</td>
                                        <td>
                                            <div class="btn-group btn-group-sm" role="group">
                                                <a href="/projects/{project.get('id')}/" class="btn btn-info">
                                                    <i class="fas fa-info-circle me-1"></i> Detalhes
                                                </a>
                                                <a href="/report/{project.get('id')}/" class="btn btn-success">
                                                    <i class="fas fa-chart-bar me-1"></i> Relatório
                                                </a>
                                            </div>
                                        </td>
                                    </tr>
            """
    else:
        content += f"""
                                    <tr>
                                        <td colspan="5" class="text-center">
                                            <div class="alert alert-info mb-0">
                                                <i class="fas fa-info-circle me-2"></i>
                                                Nenhum projeto encontrado para a busca "{search_query}".
                                            </div>
                                        </td>
                                    </tr>
        """
    
    # Fecha o conteúdo
    content += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    
    # Adicionar paginação se houver mais de uma página
    if total_pages > 1:
        # Construir a URL base para paginação, mantendo o parâmetro de busca se existir
        pagination_url = "/projects/?page="
        if search_query:
            pagination_url = f"/projects/?search={search_query}&page="
        
        # Determinar quais páginas mostrar (sempre mostrar no máximo 5 páginas)
        if total_pages <= 5:
            # Se tiver 5 ou menos páginas, mostrar todas
            page_range = range(1, total_pages + 1)
        else:
            # Se tiver mais de 5 páginas, mostrar a atual e 2 antes e depois (quando possível)
            if page <= 3:
                page_range = range(1, 6)  # Primeiras 5 páginas
            elif page >= total_pages - 2:
                page_range = range(total_pages - 4, total_pages + 1)  # Últimas 5 páginas
            else:
                page_range = range(page - 2, page + 3)  # 2 antes e 2 depois da atual
        
        # Adicionar controles de paginação
        content += f"""
        <div class="row mt-4">
            <div class="col-12">
                <nav aria-label="Navegação de páginas">
                    <ul class="pagination justify-content-center">
                        <!-- Botão Anterior -->
                        <li class="page-item {'' if page > 1 else 'disabled'}">
                            <a class="page-link" href="{pagination_url}{page-1}" aria-label="Anterior">
                                <span aria-hidden="true">&laquo;</span>
                            </a>
                        </li>
        """
        
        # Adicionar links para as páginas
        for p in page_range:
            is_active = "active" if p == page else ""
            content += f"""
                        <li class="page-item {is_active}">
                            <a class="page-link" href="{pagination_url}{p}">{p}</a>
                        </li>
            """
        
        # Adicionar botão próximo
        content += f"""
                        <!-- Botão Próximo -->
                        <li class="page-item {'' if page < total_pages else 'disabled'}">
                            <a class="page-link" href="{pagination_url}{page+1}" aria-label="Próximo">
                                <span aria-hidden="true">&raquo;</span>
                            </a>
                        </li>
                    </ul>
                </nav>
                <div class="text-center text-muted">
                    Mostrando {start_index + 1} a {end_index} de {total_projects} projetos
                </div>
            </div>
        </div>
        """
    
    # Fechar container
    content += """
    </div>
    """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, "Projetos - Gerador de Métricas GitLab")
    
    return HttpResponse(html)

def generate_ranking_html(developer_stats):
    """Gera o HTML para o ranking de desenvolvedores"""
    if not developer_stats:
        return """
        <div class="text-center py-4">
            <i class="fas fa-users fa-3x text-muted mb-3"></i>
            <p class="text-muted">Nenhum desenvolvedor encontrado para este projeto.</p>
        </div>
        """
    
    html = '<div id="ranking-container">'
    
    for i, dev in enumerate(developer_stats[:10], 1):  # Top 10
        # Definir ícone e cores da medalha
        medal_icon = ""
        medal_class = ""
        position_bg = ""
        position_text = ""
        
        if i == 1:
            medal_icon = "fas fa-trophy"
            medal_class = ""
            position_bg = "#FFD700"
            position_text = "#000"
        elif i == 2:
            medal_icon = "fas fa-medal"
            medal_class = ""
            position_bg = "#C0C0C0"
            position_text = "#000"
        elif i == 3:
            medal_icon = "fas fa-award"
            medal_class = ""
            position_bg = "#CD7F32"
            position_text = "#fff"
        else:
            medal_icon = "fas fa-star"
            medal_class = ""
            position_bg = "#6c757d"
            position_text = "#fff"
        
        # Calcular total de mudanças
        total_changes = dev.get('additions', 0) + dev.get('deletions', 0)
        
        # Definir cor de fundo do item baseada na posição
        item_bg = ""
        if i <= 3:
            item_bg = "background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 165, 0, 0.05));"
        elif i <= 5:
            item_bg = "background: linear-gradient(135deg, rgba(192, 192, 192, 0.1), rgba(168, 168, 168, 0.05));"
        else:
            item_bg = "background: linear-gradient(135deg, rgba(108, 117, 125, 0.1), rgba(73, 80, 87, 0.05));"
        
        html += f"""
        <div class="ranking-item mb-3 p-3 border rounded shadow-sm" 
             data-commits="{dev.get('commits', 0)}" 
             data-additions="{dev.get('additions', 0)}" 
             data-deletions="{dev.get('deletions', 0)}"
             style="{item_bg} border-left: 4px solid {position_bg};">
            <div class="d-flex align-items-center">
                <div class="position me-3">
                    <div class="medal-container" style="
                        width: 50px; 
                        height: 50px; 
                        background: {position_bg}; 
                        border-radius: 50%; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        position: relative;
                    ">
                        <i class="{medal_icon} {medal_class}" style="font-size: 1.2rem; color: {position_text};"></i>
                        <div class="position-number" style="
                            position: absolute; 
                            bottom: -5px; 
                            right: -5px; 
                            background: #fff; 
                            color: #000; 
                            border-radius: 50%; 
                            width: 20px; 
                            height: 20px; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center; 
                            font-size: 0.7rem; 
                            font-weight: bold;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        ">#{i}</div>
                    </div>
                </div>
                <div class="developer-info flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <i class="fas fa-user-circle me-2 text-primary"></i>
                        <h6 class="mb-0 fw-bold">{dev.get('name', 'Desconhecido')}</h6>
                        {f'<span class="badge bg-success ms-2">Top {i}</span>' if i <= 3 else ''}
                    </div>
                    <small class="text-muted">
                        <i class="fas fa-envelope me-1"></i>
                        {dev.get('email', '')}
                    </small>
                </div>
                <div class="stats">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="stat-item text-center" style="min-width: 80px;">
                            <i class="fas fa-code-branch text-primary mb-1 d-block"></i>
                            <div class="fw-bold text-primary fs-5">{dev.get('commits', 0)}</div>
                            <small class="text-muted">Commits</small>
                        </div>
                        <div class="stat-item text-center" style="min-width: 80px;">
                            <i class="fas fa-plus text-success mb-1 d-block"></i>
                            <div class="fw-bold text-success fs-5">+{dev.get('additions', 0)}</div>
                            <small class="text-muted">Adições</small>
                        </div>
                        <div class="stat-item text-center" style="min-width: 80px;">
                            <i class="fas fa-minus text-danger mb-1 d-block"></i>
                            <div class="fw-bold text-danger fs-5">-{dev.get('deletions', 0)}</div>
                            <small class="text-muted">Remoções</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    html += '</div>'
    
    return html

def project_detail(request, project_id):
    """Detalhes de um projeto específico"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Busca os dados do projeto
    response = requests.get(
        get_api_url(request, f'gitlab/projects/{project_id}/'),
        cookies=request.COOKIES,
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar projeto')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar projeto (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('project-list')
    
    try:
        project = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('project-list')
    
    # Busca estatísticas de desenvolvedores para o ranking
    stats_response = requests.get(
        get_api_url(request, f'gitlab/projects/{project_id}/stats/'),
        cookies=request.COOKIES,
    )
    
    developer_stats = []
    if stats_response.status_code == 200:
        try:
            developer_stats = stats_response.json()
            # Ordenar por número de commits (ranking)
            developer_stats.sort(key=lambda x: x.get('commits', 0), reverse=True)
        except (ValueError, requests.exceptions.JSONDecodeError):
            developer_stats = []
    
    # Conteúdo da página
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1 class="mb-0">{project['name']}</h1>
                    <div>
                        <a href="/report/{project_id}/" class="btn btn-success me-2">
                            <i class="fas fa-chart-bar me-2"></i> Gerar Relatório
                        </a>
                        <a href="/projects/" class="btn btn-outline-secondary" onclick="history.back(); return false;">
                            <i class="fas fa-arrow-left me-2"></i> Voltar
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-info-circle me-2"></i>
                            Informações do Projeto
                        </h5>
                    </div>
                    <div class="card-body">
                        <dl class="row">
                            <dt class="col-sm-3">ID:</dt>
                            <dd class="col-sm-9">{project['id']}</dd>
                            
                            <dt class="col-sm-3">Nome:</dt>
                            <dd class="col-sm-9">{project['name']}</dd>
                            
                            <dt class="col-sm-3">Namespace:</dt>
                            <dd class="col-sm-9">{project['name_with_namespace']}</dd>
                            
                            <dt class="col-sm-3">Descrição:</dt>
                            <dd class="col-sm-9">{project.get('description', 'Sem descrição')}</dd>
                            
                            <dt class="col-sm-3">URL:</dt>
                            <dd class="col-sm-9">
                                <a href="{project.get('web_url', '#')}" target="_blank" class="text-decoration-none">
                                    {project.get('web_url', 'N/A')}
                                    <i class="fas fa-external-link-alt ms-1"></i>
                                </a>
                            </dd>
                            
                            <dt class="col-sm-3">Última Atividade:</dt>
                            <dd class="col-sm-9">{project.get('last_activity_at', 'N/A')}</dd>
                            
                            <dt class="col-sm-3">Criado em:</dt>
                            <dd class="col-sm-9">{project.get('created_at', 'N/A')}</dd>
                        </dl>
                    </div>
                </div>
                
                <!-- Ranking de Desenvolvedores -->
                <div class="card mb-4">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 class="mb-0">
                                <i class="fas fa-trophy me-2 text-warning"></i>
                                Ranking de Desenvolvedores
                            </h5>
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-outline-primary btn-sm active" onclick="sortRanking('commits')">
                                    <i class="fas fa-code-branch me-1"></i> Commits
                                </button>
                                <button type="button" class="btn btn-outline-success btn-sm" onclick="sortRanking('additions')">
                                    <i class="fas fa-plus me-1"></i> Adições
                                </button>
                                <button type="button" class="btn btn-outline-danger btn-sm" onclick="sortRanking('deletions')">
                                    <i class="fas fa-minus me-1"></i> Remoções
                                </button>
                            </div>
                        </div>
                        
                        <!-- Filtros de Período -->
                        <form id="ranking-filter-form" class="row g-3">
                            <div class="col-md-4">
                                <label for="start-date" class="form-label">Data Inicial</label>
                                <input type="date" class="form-control" id="start-date" name="start_date" 
                                       value="{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}">
                            </div>
                            <div class="col-md-4">
                                <label for="end-date" class="form-label">Data Final</label>
                                <input type="date" class="form-control" id="end-date" name="end_date" 
                                       value="{datetime.now().strftime('%Y-%m-%d')}">
                            </div>
                            <div class="col-md-4 d-flex align-items-end">
                                <button type="button" class="btn btn-primary me-2" onclick="updateRanking()">
                                    <i class="fas fa-filter me-1"></i> Filtrar
                                </button>
                                <button type="button" class="btn btn-outline-secondary" onclick="resetRanking()">
                                    <i class="fas fa-undo me-1"></i> Resetar
                                </button>
                            </div>
                        </form>
                    </div>
                    <div class="card-body">
                        <div id="ranking-loading" class="text-center py-4" style="display: none;">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Carregando...</span>
                            </div>
                            <p class="mt-2">Atualizando ranking...</p>
                        </div>
                        <div id="ranking-content">
                            {generate_ranking_html(developer_stats)}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-chart-pie me-2"></i>
                            Estatísticas
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-6 mb-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-primary mb-1">{project.get('star_count', 0)}</h4>
                                    <small class="text-muted">Stars</small>
                                </div>
                            </div>
                            <div class="col-6 mb-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-success mb-1">{project.get('forks_count', 0)}</h4>
                                    <small class="text-muted">Forks</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-cogs me-2"></i>
                            Ações
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <a href="/report/{project_id}/" class="btn btn-success">
                                <i class="fas fa-chart-bar me-2"></i> Gerar Relatório
                            </a>
                            <a href="/projects/{project_id}/commits/" class="btn btn-info">
                                <i class="fas fa-code-branch me-2"></i> Ver Commits
                            </a>
                            <a href="{project.get('web_url', '#')}" target="_blank" class="btn btn-outline-primary">
                                <i class="fas fa-external-link-alt me-2"></i> Abrir no GitLab
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, f"{project['name']} - Gerador de Métricas GitLab")
    
    return HttpResponse(html)

def report(request):
    """Página de seleção de relatórios"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Obter termo de busca e página atual
    search_query = request.GET.get('search', '')
    page = int(request.GET.get('page', '1'))
    per_page = 12  # Número de projetos por página (3 colunas x 4 linhas)
    
    # Busca os projetos via API interna
    response = requests.get(
        get_api_url(request, 'gitlab/projects/'),
        cookies=request.COOKIES,
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar projetos')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar projetos (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('home')
    
    # Obter todos os projetos
    try:
        projects = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('home')
    
    # Filtrar projetos manualmente (mais simples e garantido)
    if search_query and search_query.strip():
        search_term = search_query.lower().strip()
        filtered_projects = []
        
        for project in projects:
            name = str(project.get('name', '')).lower()
            namespace = str(project.get('name_with_namespace', '')).lower()
            
            if search_term in name or search_term in namespace:
                filtered_projects.append(project)
    else:
        filtered_projects = projects
    
    # Calcular paginação
    total_projects = len(filtered_projects)
    total_pages = (total_projects + per_page - 1) // per_page  # Arredonda para cima
    
    # Ajustar página atual se estiver fora dos limites
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calcular índices de início e fim para a página atual
    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, total_projects)
    
    # Obter projetos da página atual
    current_page_projects = filtered_projects[start_index:end_index]
    
    # Conteúdo da página
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1 class="mb-0">Relatórios de Métricas <span class="badge bg-success">{len(filtered_projects)}</span></h1>
                    <a href="/" class="btn btn-outline-secondary" onclick="history.back(); return false;">
                        <i class="fas fa-arrow-left me-2"></i> Voltar
                    </a>
                </div>
            </div>
        </div>

        <!-- Campo de busca -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <form method="get" class="row g-3">
                            <div class="col-md-10">
                                <div class="input-group">
                                    <span class="input-group-text"><i class="fas fa-search"></i></span>
                                    <input type="text" name="search" class="form-control" placeholder="Buscar projeto por nome..." value="{search_query}">
                                </div>
                            </div>
                            <div class="col-md-2">
                                <button type="submit" class="btn btn-primary w-100" id="searchButton">
                                    <i class="fas fa-search me-2"></i> Buscar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">Selecione um Projeto para Gerar Relatório</h5>
                            <span class="text-muted">{len(filtered_projects)} projetos {f'encontrados para "{search_query}"' if search_query else 'disponíveis'}</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row row-cols-1 row-cols-md-3 g-4">
    """
    
    # Adicionar cards de projetos
    if current_page_projects:
        for project in current_page_projects:
            description = project.get('description', '') or 'Sem descrição'
            content += f"""
                                <div class="col">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h5 class="card-title">{project.get('name', '')}</h5>
                                            <h6 class="card-subtitle mb-2 text-muted">{project.get('name_with_namespace', '')}</h6>
                                            <p class="card-text">{description}</p>
                                        </div>
                                        <div class="card-footer">
                                            <a href="/report/{project.get('id')}/" class="btn btn-primary w-100">
                                                <i class="fas fa-chart-bar me-2"></i> Gerar Relatório
                                            </a>
                                        </div>
                                    </div>
                                </div>
            """
    else:
        content += f"""
                                <div class="col-12">
                                    <div class="alert alert-info">
                                        <i class="fas fa-info-circle me-2"></i>
                                        Nenhum projeto encontrado para a busca "{search_query}".
                                    </div>
                                </div>
        """
    
    # Fecha o conteúdo
    content += """
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    
    # Adicionar paginação se houver mais de uma página
    if total_pages > 1:
        # Construir a URL base para paginação, mantendo o parâmetro de busca se existir
        pagination_url = "/report/?page="
        if search_query:
            pagination_url = f"/report/?search={search_query}&page="
        
        # Determinar quais páginas mostrar (sempre mostrar no máximo 5 páginas)
        if total_pages <= 5:
            # Se tiver 5 ou menos páginas, mostrar todas
            page_range = range(1, total_pages + 1)
        else:
            # Se tiver mais de 5 páginas, mostrar a atual e 2 antes e depois (quando possível)
            if page <= 3:
                page_range = range(1, 6)  # Primeiras 5 páginas
            elif page >= total_pages - 2:
                page_range = range(total_pages - 4, total_pages + 1)  # Últimas 5 páginas
            else:
                page_range = range(page - 2, page + 3)  # 2 antes e 2 depois da atual
        
        # Adicionar controles de paginação
        content += f"""
        <div class="row mt-4">
            <div class="col-12">
                <nav aria-label="Navegação de páginas">
                    <ul class="pagination justify-content-center">
                        <!-- Botão Anterior -->
                        <li class="page-item {'' if page > 1 else 'disabled'}">
                            <a class="page-link" href="{pagination_url}{page-1}" aria-label="Anterior">
                                <span aria-hidden="true">&laquo;</span>
                            </a>
                        </li>
        """
        
        # Adicionar links para as páginas
        for p in page_range:
            is_active = "active" if p == page else ""
            content += f"""
                        <li class="page-item {is_active}">
                            <a class="page-link" href="{pagination_url}{p}">{p}</a>
                        </li>
            """
        
        # Adicionar botão próximo
        content += f"""
                        <!-- Botão Próximo -->
                        <li class="page-item {'' if page < total_pages else 'disabled'}">
                            <a class="page-link" href="{pagination_url}{page+1}" aria-label="Próximo">
                                <span aria-hidden="true">&raquo;</span>
                            </a>
                        </li>
                    </ul>
                </nav>
                <div class="text-center text-muted">
                    Mostrando {start_index + 1} a {end_index} de {total_projects} projetos
                </div>
            </div>
        </div>
        """
    
    # Fechar container
    content += """
    </div>
    """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, "Relatórios - Gerador de Métricas GitLab")
    
    return HttpResponse(html)

def report_detail(request, project_id):
    """Relatório detalhado por desenvolvedor"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Parâmetros de data (opcional) - aceita tanto since/until quanto start_date/end_date
    since = request.GET.get('since')
    until = request.GET.get('until')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Usar since/until se fornecidos, caso contrário usar start_date/end_date
    if not since and start_date:
        since = start_date
    if not until and end_date:
        until = end_date
    
    # Normalizar formatos de data (aceitar DD/MM/YYYY além de YYYY-MM-DD)
    def _normalize_date(date_str):
        if not date_str:
            return date_str
        if '/' in date_str:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            except Exception:
                pass
        return date_str

    since = _normalize_date(since)
    until = _normalize_date(until)

    # Se não especificado, usa o último mês
    if not since:
        since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not until:
        until = datetime.now().strftime('%Y-%m-%d')
        
    # Usar since/until como as variáveis principais para exibição e API
    start_date = since
    end_date = until
    
    # Fazer consulta com as datas (agora sempre temos valores)
    stats = []
    # Adicionar timestamp para evitar cache do navegador
    timestamp = int(time.time())
    
    response = requests.get(
        get_api_url(request, f'gitlab/projects/{project_id}/stats/'),
        params={
            'since': since, 
            'until': until,
            '_': timestamp  # Prevenir cache do navegador
        },
        cookies=request.COOKIES
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar estatísticas')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar estatísticas (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('report')
    
    try:
        stats = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('report')
    
    # Busca os dados do projeto para exibir o nome
    project_response = requests.get(
        get_api_url(request, 'gitlab/projects/'),
        cookies=request.COOKIES,
    )
    
    project_name = f"Projeto #{project_id}"
    if project_response.status_code == 200:
        projects = project_response.json()
        for project in projects:
            if project['id'] == project_id:
                project_name = project['name_with_namespace']
                break
    
    # Conteúdo da página
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div class="card mb-4">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">Métricas de Contribuição - {project_name}</h4>
                        <div>
                            <div class="btn-group">
                                <a href="/export/{project_id}/?format=csv&since={start_date}&until={end_date}" class="btn btn-outline-success">
                                    <i class="fas fa-file-csv me-2"></i> Exportar CSV
                                </a>
                                <a href="/export/{project_id}/?format=json&since={start_date}&until={end_date}" class="btn btn-outline-primary">
                                    <i class="fas fa-file-code me-2"></i> Exportar JSON
                                </a>
                            </div>
                            <a href="/report/" class="btn btn-outline-secondary ms-2" onclick="history.back(); return false;">
                                <i class="fas fa-arrow-left me-2"></i> Voltar
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Filtro de datas -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Filtrar por Período</h5>
                        <form method="get" id="date-filter-form" class="row g-3" action="{request.path}">
                            <div class="col-md-5">
                                <label class="form-label" for="since-input">Data Inicial</label>
                                <input type="date" name="since" id="since-input" class="form-control" value="{start_date}" required>
                            </div>
                            <div class="col-md-5">
                                <label class="form-label" for="until-input">Data Final</label>
                                <input type="date" name="until" id="until-input" class="form-control" value="{end_date}" required>
                            </div>
                            <div class="col-md-2 d-flex align-items-end">
                                <button type="submit" id="filter-button" class="btn btn-primary w-100">
                                    <i class="fas fa-filter me-2"></i> Filtrar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Período atual -->
        {f'''
        <div class="alert alert-light border mb-4">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="fas fa-calendar me-2"></i>
                    <strong>Período:</strong> {start_date} até {end_date}
                </div>
                <div>
                    <span class="badge bg-info">Filtro aplicado</span>
                </div>
            </div>
        </div>
        '''}
    """
    
    # Verificar se há estatísticas
    if stats:
        # Tabela de dados
        content += """
        <!-- Tabela com detalhes -->
        <div class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Detalhes por Desenvolvedor</h5>
                <span class="badge bg-info">
                    <i class="fas fa-calendar me-1"></i>
                    """ + f"{start_date} até {end_date}" + """
                </span>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Desenvolvedor</th>
                                <th>Email</th>
                                <th>Commits</th>
                                <th>Linhas Adicionadas</th>
                                <th>Linhas Removidas</th>
                                <th>Total</th>
                                <th>Branches</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Adicionar linhas na tabela
        for dev in stats:
            total = dev.get('additions', 0) + dev.get('deletions', 0)
            
            # Processar informações de branches
            branches_info = dev.get('branches', {})
            branches_html = ""
            
            if branches_info:
                # Ordenar branches por número de commits (maior primeiro)
                sorted_branches = sorted(branches_info.items(), 
                                       key=lambda x: x[1].get('commits', 0), 
                                       reverse=True)
                
                branch_badges = []
                for branch_name, branch_stats in sorted_branches:
                    commits_count = branch_stats.get('commits', 0)
                    additions = branch_stats.get('additions', 0)
                    deletions = branch_stats.get('deletions', 0)
                    
                    # Determinar cor do badge baseado no tipo de branch
                    if branch_name == 'multiple':
                        badge_class = 'bg-info'
                        display_name = 'Múltiplas'
                    elif branch_name in ['main', 'master', 'develop']:
                        badge_class = 'bg-primary'
                        display_name = branch_name
                    else:
                        badge_class = 'bg-secondary'
                        display_name = branch_name
                    
                    # Criar tooltip com detalhes da branch
                    tooltip = f"Commits: {commits_count}, +{additions}/-{deletions}"
                    branch_badges.append(
                        f'<span class="badge {badge_class}" title="{tooltip}">{display_name}</span>'
                    )
                
                branches_html = ' '.join(branch_badges)
            else:
                branches_html = '<span class="badge bg-light text-dark">N/A</span>'
            
            content += f"""
                            <tr>
                                <td>{dev.get('name', '')}</td>
                                <td>{dev.get('email', '')}</td>
                                <td>{dev.get('commits', 0)}</td>
                                <td class="text-success">+{dev.get('additions', 0)}</td>
                                <td class="text-danger">-{dev.get('deletions', 0)}</td>
                                <td>{total}</td>
                                <td>{branches_html}</td>
                            </tr>
            """
        
        # Fechar tabela
        content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        
        # Gráficos
        content += """
        <!-- Gráficos -->
        <div class="row mb-4">
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Linhas Adicionadas por Desenvolvedor</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="additionsChart" height="300"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Linhas Removidas por Desenvolvedor</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="deletionsChart" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Commits por Desenvolvedor</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="commitsChart" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>
        """
        
        # JavaScript para os gráficos
        content += f"""
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Dados para os gráficos
            const developers = {json.dumps(stats)};
            const names = developers.map(dev => dev.name);
            const additions = developers.map(dev => dev.additions);
            const deletions = developers.map(dev => dev.deletions);
            const commits = developers.map(dev => dev.commits);

            // Cores para os gráficos
            const backgroundColors = [
                'rgba(54, 162, 235, 0.7)', 
                'rgba(255, 99, 132, 0.7)',
                'rgba(255, 206, 86, 0.7)',
                'rgba(75, 192, 192, 0.7)',
                'rgba(153, 102, 255, 0.7)',
                'rgba(255, 159, 64, 0.7)',
                'rgba(199, 199, 199, 0.7)',
                'rgba(83, 102, 255, 0.7)',
                'rgba(40, 159, 64, 0.7)',
                'rgba(210, 199, 199, 0.7)'
            ];

            // Função para criar gráfico de barras
            function createBarChart(elementId, labels, data, label, backgroundColor) {{
                const canvas = document.getElementById(elementId);
                if (!canvas) {{
                    console.warn('Canvas element not found:', elementId);
                    return;
                }}
                const ctx = canvas.getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: label,
                            data: data,
                            backgroundColor: backgroundColor,
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }});
            }}

            // Criar os gráficos
            createBarChart('additionsChart', names, additions, 'Linhas Adicionadas', 
                        names.map((_, i) => backgroundColors[i % backgroundColors.length]));
            
            createBarChart('deletionsChart', names, deletions, 'Linhas Removidas', 
                        names.map((_, i) => backgroundColors[i % backgroundColors.length]));
            
            createBarChart('commitsChart', names, commits, 'Número de Commits', 
                        names.map((_, i) => backgroundColors[i % backgroundColors.length]));
        }});
        </script>
        """
    else:
        # Se não houver estatísticas ou datas selecionadas
        if not start_date or not end_date:
            # Estado vazio - usuário precisa selecionar datas
            content += """
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-body text-center py-5">
                            <div class="mb-4">
                                <i class="fas fa-calendar-alt fa-3x text-muted"></i>
                            </div>
                            <h4 class="text-muted mb-3">Selecione um Período</h4>
                            <p class="text-muted mb-4">
                                Escolha as datas inicial e final no filtro acima para visualizar as métricas de contribuição do projeto.
                            </p>
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Dica:</strong> Use o filtro de datas no topo da página para definir o período desejado.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        else:
            # Datas selecionadas mas nenhuma estatística encontrada
            content += """
        <div class="row">
            <div class="col-12">
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Nenhuma estatística encontrada para o período selecionado.
                </div>
            </div>
        </div>
        """
    
    # Fechar container
    content += """
    </div>
    """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, f"{project_name} - Relatório de Métricas")
    
    return HttpResponse(html)

def export_report(request, project_id):
    """Exporta o relatório em formato CSV ou JSON"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Parâmetros de data e formato - aceita tanto since/until quanto start_date/end_date
    since = request.GET.get('since')
    until = request.GET.get('until')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    format_type = request.GET.get('format', 'csv').lower()
    
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
    

    
    # Busca as estatísticas do projeto
    response = requests.get(
        get_api_url(request, f'gitlab/projects/{project_id}/stats/'),
        params={'since': since, 'until': until},
        cookies=request.COOKIES,
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar estatísticas')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar estatísticas (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('report')
    
    try:
        stats = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('report')
    
    # Nome do arquivo
    filename = f"gitlab-metrics-project-{project_id}-{datetime.now().strftime('%Y%m%d')}"
    
    if format_type == 'json':
        # Exporta como JSON
        response = HttpResponse(json.dumps(stats, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
    else:
        # Exporta como CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Desenvolvedor', 'Email', 'Commits', 'Linhas Adicionadas', 'Linhas Removidas', 'Total de Alterações', 'Branches'])
        
        for dev in stats:
            # Processar informações de branches para CSV
            branches_info = dev.get('branches', {})
            branches_text = ""
            
            if branches_info:
                # Ordenar branches por número de commits (maior primeiro)
                sorted_branches = sorted(branches_info.items(), 
                                       key=lambda x: x[1].get('commits', 0), 
                                       reverse=True)
                
                branch_details = []
                for branch_name, branch_stats in sorted_branches:
                    commits_count = branch_stats.get('commits', 0)
                    additions = branch_stats.get('additions', 0)
                    deletions = branch_stats.get('deletions', 0)
                    
                    display_name = 'Múltiplas' if branch_name == 'multiple' else branch_name
                    branch_details.append(f"{display_name}({commits_count} commits, +{additions}/-{deletions})")
                
                branches_text = "; ".join(branch_details)
            else:
                branches_text = "N/A"
            
            writer.writerow([
                dev['name'],
                dev['email'],
                dev['commits'],
                dev['additions'],
                dev['deletions'],
                dev['additions'] + dev['deletions'],
                branches_text
            ])
    
    return response






def project_commits(request, project_id):
    """Página de commits por desenvolvedor"""
    # Garante que o token esteja na sessão
    if 'gitlab_token' not in request.session:
        request.session['gitlab_token'] = settings.GITLAB_TOKEN
    
    # Parâmetros de data (opcional) - aceita tanto since/until quanto start_date/end_date
    since = request.GET.get('since')
    until = request.GET.get('until')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Usar since/until se fornecidos, caso contrário usar start_date/end_date
    if not since and start_date:
        since = start_date
    if not until and end_date:
        until = end_date
    
    # Normalizar formatos de data (aceitar DD/MM/YYYY além de YYYY-MM-DD)
    def _normalize_date(date_str):
        if not date_str:
            return date_str
        if '/' in date_str:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            except Exception:
                pass
        return date_str

    since = _normalize_date(since)
    until = _normalize_date(until)

    # Se não especificado, usa o último mês
    if not since:
        since = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not until:
        until = datetime.now().strftime('%Y-%m-%d')
        
    # Usar since/until como as variáveis principais para exibição e API
    start_date = since
    end_date = until
    

    
    # Busca os commits do projeto
    response = requests.get(
        get_api_url(request, f'gitlab/projects/{project_id}/commits/'),
        params={'since': start_date, 'until': end_date},
        cookies=request.COOKIES,
    )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', 'Erro ao buscar commits')
        except (ValueError, requests.exceptions.JSONDecodeError):
            error_msg = f'Erro ao buscar commits (Status: {response.status_code})'
        messages.error(request, error_msg)
        return redirect('project-list')
    
    try:
        commits = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        messages.error(request, 'Erro ao processar resposta da API: dados inválidos')
        return redirect('project-list')
    
    # Busca os dados do projeto para exibir o nome
    project_response = requests.get(
        get_api_url(request, 'gitlab/projects/'),
        cookies=request.COOKIES,
    )
    
    project_name = f"Projeto #{project_id}"
    if project_response.status_code == 200:
        projects = project_response.json()
        for project in projects:
            if project['id'] == project_id:
                project_name = project['name_with_namespace']
                break
    
    # Agrupar commits por desenvolvedor
    commits_by_developer = {}
    for commit in commits:
        author_email = commit.get('author_email', '')
        author_name = commit.get('author_name', '')
        
        if author_email not in commits_by_developer:
            commits_by_developer[author_email] = {
                'name': author_name,
                'email': author_email,
                'commits': []
            }
        
        commits_by_developer[author_email]['commits'].append(commit)
    
    # Conteúdo da página
    content = f"""
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1 class="mb-0">Commits por Desenvolvedor</h1>
                    <div>
                        <a href="/projects/{project_id}/" class="btn btn-outline-secondary me-2">
                            <i class="fas fa-arrow-left me-2"></i> Voltar
                        </a>
                        <a href="/report/{project_id}/" class="btn btn-success">
                            <i class="fas fa-chart-bar me-2"></i> Ver Relatório
                        </a>
                    </div>
                </div>
                <h2 class="text-muted mb-4">{project_name}</h2>
            </div>
        </div>
        
        <!-- Filtro de datas -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Filtrar por Período</h5>
                        
                        <form method="get" id="date-filter-form" class="row g-3" action="{request.path}">
                            <div class="col-md-5">
                                <label class="form-label" for="since-input">Data Inicial</label>
                                <input type="date" name="since" id="since-input" class="form-control" value="{start_date}" required>
                            </div>
                            <div class="col-md-5">
                                <label class="form-label" for="until-input">Data Final</label>
                                <input type="date" name="until" id="until-input" class="form-control" value="{end_date}" required>
                            </div>
                            <div class="col-md-2 d-flex align-items-end">
                                <button type="submit" id="filter-button" class="btn btn-primary w-100">
                                    <i class="fas fa-filter me-2"></i> Filtrar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- Resumo -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Resumo do Período</h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-md-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-primary mb-1">{len(commits_by_developer)}</h4>
                                    <small class="text-muted">Desenvolvedores</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-success mb-1">{len(commits)}</h4>
                                    <small class="text-muted">Total de Commits</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-info mb-1">{start_date}</h4>
                                    <small class="text-muted">Data Inicial</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="border rounded p-3">
                                    <h4 class="text-warning mb-1">{end_date}</h4>
                                    <small class="text-muted">Data Final</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """
    
    # Adicionar seções por desenvolvedor
    if commits_by_developer:
        for email, dev_data in commits_by_developer.items():
            commits_count = len(dev_data['commits'])
            content += f"""
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">
                                <i class="fas fa-user me-2"></i>
                                {dev_data['name']}
                            </h5>
                            <span class="badge bg-primary">{commits_count} commits</span>
                        </div>
                        <small class="text-muted">{dev_data['email']}</small>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-sm">
                                <thead>
                                    <tr>
                                        <th>Commit</th>
                                        <th>Data</th>
                                        <th>Branch</th>
                                        <th>Mensagem</th>
                                    </tr>
                                </thead>
                                <tbody>
            """
            
            for commit in dev_data['commits']:
                formatted_date = commit.get('authored_date', '')
                try:
                    # Converter formato ISO para objeto datetime e depois para formato legível
                    dt = datetime.fromisoformat(formatted_date.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
                
                # Obter informações de branch
                branch_name = commit.get('branch_name', 'N/A')
                ref_name = commit.get('ref_name', 'N/A')
                
                # Usar branch_name se disponível, senão ref_name, senão 'N/A'
                display_branch = branch_name if branch_name != 'N/A' else (ref_name if ref_name != 'N/A' else 'N/A')
                
                # Adicionar badge para branch
                if display_branch == 'multiple':
                    branch_badge = '<span class="badge bg-info">Múltiplas</span>'
                elif display_branch != 'N/A':
                    branch_badge = f'<span class="badge bg-secondary">{display_branch}</span>'
                else:
                    branch_badge = '<span class="badge bg-light text-dark">N/A</span>'
                
                content += f"""
                                    <tr>
                                        <td><code>{commit.get('short_id', '')}</code></td>
                                        <td>{formatted_date}</td>
                                        <td>{branch_badge}</td>
                                        <td>{commit.get('title', '')}</td>
                                    </tr>
                """
            
            content += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
            """
    else:
        content += """
        <div class="row">
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Nenhum commit encontrado no período selecionado.
                </div>
            </div>
        </div>
        """
    
    # Insere o conteúdo no template base
    html = insert_content_into_sidebar_template(content, f"{project_name} - Commits por Desenvolvedor")
    
    return HttpResponse(html)

