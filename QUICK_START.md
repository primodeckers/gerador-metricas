# 🚀 Quick Start - Gerador de Métricas GitLab

## Deploy Rápido

### 1. Configuração Inicial

```bash
# Copiar arquivo de ambiente
cp environment.env .env

# Editar configurações (opcional)
nano .env
```

### 2. Deploy com Docker Compose

```bash
# Build e start
docker-compose up -d --build

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### 3. Testar Aplicação

```bash
# Health check
curl http://localhost:8000/api/health/

# Acessar no navegador
# http://localhost:8000
```

## Comandos Úteis

### Gerenciamento de Container

```bash
# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Rebuild completo
docker-compose down --rmi all
docker-compose up -d --build
```

### Logs e Debug

```bash
# Ver logs em tempo real
docker-compose logs -f web

# Entrar no container
docker-compose exec web bash

# Executar comandos Django
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Backup

```bash
# Backup do banco
cp ./data/db.sqlite3 backup/db-$(date +%Y%m%d).sqlite3

# Backup completo
tar -czf backup-$(date +%Y%m%d).tar.gz data/ staticfiles/
```

## Configurações Importantes

### Variáveis de Ambiente Essenciais

- `SECRET_KEY`: Chave secreta do Django (mude em produção!)
- `GITLAB_TOKEN`: Token de acesso ao GitLab
- `ALLOWED_HOSTS`: Hosts permitidos (domínio em produção)

### Volumes

- `./data`: Banco SQLite persistente
- `./staticfiles`: Arquivos estáticos
- `./logs`: Logs da aplicação

## Troubleshooting

### Container não inicia

```bash
# Verificar logs
docker-compose logs web

# Verificar portas
netstat -tulpn | grep 8000
```

### Problemas de permissão

```bash
# Ajustar permissões
sudo chown -R 1000:1000 ./data
sudo chown -R 1000:1000 ./staticfiles
```

### Reset completo

```bash
# Parar e remover tudo
docker-compose down -v --rmi all

# Remover volumes
docker volume prune

# Rebuild
docker-compose up -d --build
```

## Produção

Para deploy em produção, use:

```bash
# Usar configuração de produção
cp environment.prod.env .env

# Deploy com configurações de produção
docker-compose -f docker-compose.prod.yml up -d --build
```

## URLs Importantes

- **Aplicação**: http://localhost:8000
- **API Health**: http://localhost:8000/api/health/
- **API Projetos**: http://localhost:8000/api/gitlab/projects/
- **Admin Django**: http://localhost:8000/admin/ (admin/admin123)
