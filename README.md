# Gerador de Métricas GitLab

Sistema Django para análise de contribuições de código em repositórios GitLab com **contagem real de linhas de código excluindo comentários**.

## 🚀 Funcionalidades

- **Contagem precisa de código**: Distingue entre linhas de código, comentários e linhas em branco
- **Suporte a 16 linguagens**: Python, JavaScript, Java, C++, PHP, Ruby, Go, Rust, HTML, CSS, SQL, XML, YAML, JSON, Markdown
- **Análise por desenvolvedor**: Métricas detalhadas de contribuição individual
- **Interface moderna**: Cards de projetos recentes com carregamento otimizado
- **Relatórios exportáveis**: CSV e JSON com dados completos
- **Performance otimizada**: Cache inteligente e processamento em lotes

## 📋 Requisitos

- Python 3.8+
- Django 5.0+
- Django REST Framework
- python-gitlab
- Chart.js (CDN incluído)
- Bootstrap 5 (CDN incluído)

## 🔧 Tecnologias

- **Backend**: Django + Django REST Framework
- **Frontend**: Bootstrap 5 + Chart.js
- **Integração**: GitLab API v4
- **Cache**: Django Cache Framework
- **Parser**: Regex otimizado para múltiplas linguagens

## ⚡ Instalação Rápida

```bash
# 1. Clone o repositório
git clone <URL-DO-REPOSITORIO>
cd gerador-metricas

# 2. Configure o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute as migrações
python manage.py migrate

# 5. Inicie o servidor
python manage.py runserver
```

Acesse: `http://localhost:8000`

## 🎯 Como Usar

1. **Configure seu token GitLab** na página inicial
   - Permissões necessárias: `read_api` e `read_repository`
2. **Explore os projetos** na lista de repositórios disponíveis
3. **Visualize commits recentes** nos cards de projetos
4. **Gere relatórios detalhados** por desenvolvedor com:
   - Contagem real de linhas de código (excluindo comentários)
   - Estatísticas por linguagem de programação
   - Gráficos interativos de contribuição
   - Exportação em CSV/JSON

## ⚙️ Configuração

Para GitLab self-hosted, edite `GITLAB_API_URL` em `settings.py`:

```python
GITLAB_API_URL = "https://seu-gitlab.com/"
```

## 🔒 Segurança

- ✅ Tokens armazenados apenas na sessão
- ✅ Nenhum dado persistido no banco
- ✅ Sessão expira automaticamente
- ✅ SSL/TLS para comunicação segura

## 📊 Exemplo de Métricas

```json
{
  "desenvolvedor": "João Silva",
  "commits": 25,
  "linhas_codigo_adicionadas": 1.25,
  "linhas_codigo_removidas": 320,
  "linhas_comentarios": 180,
  "linhas_branco": 95
}
```
