# Deploy do Gerador de Métricas GitLab

Este documento contém instruções para fazer o deploy da aplicação em produção usando Docker.

## Arquivos de Configuração

### 1. Dockerfile

- Imagem base: Python 3.11-slim
- Usuário não-root para segurança
- Otimizações para produção
- Health check configurado

### 2. environment.env

Arquivo de configuração de ambiente com todas as variáveis necessárias:

- Configurações do Django
- Configurações do GitLab API
- Configurações de segurança
- Configurações de CORS
- Configurações de cache e sessão

### 3. docker-compose.yml

Orquestração do container com:

- Volume para persistência do banco SQLite
- Volume para arquivos estáticos
- Health check
- Restart automático

## Como Fazer o Deploy

### 1. Preparação do Ambiente

```bash
# Clone o repositório
git clone <seu-repositorio>
cd gerador-metricas

# Copie o arquivo de ambiente
cp environment.env .env

# Edite as configurações conforme necessário
nano .env
```

### 2. Configurações Importantes

No arquivo `.env`, ajuste as seguintes configurações:

```env
# Mude para uma chave secreta segura
SECRET_KEY=sua-chave-secreta-super-segura-aqui

# Configure os hosts permitidos
ALLOWED_HOSTS=seu-dominio.com,www.seu-dominio.com

# Configure as origens CORS
CORS_ALLOWED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com

# Configure o token do GitLab
GITLAB_TOKEN=seu-token-do-gitlab-aqui
```

### 3. Build e Deploy

```bash
# Build da imagem
docker build -t gerador-metricas .

# Ou usando docker-compose
docker-compose up -d --build
```

### 4. Verificação

```bash
# Verificar se o container está rodando
docker-compose ps

# Verificar logs
docker-compose logs -f

# Testar a aplicação
curl http://localhost:8000/api/health/
```

## Estrutura de Volumes

- `./data:/app/data` - Banco SQLite persistente
- `./staticfiles:/app/staticfiles` - Arquivos estáticos

## Configurações de Segurança

- Usuário não-root no container
- Headers de segurança configurados
- CORS restritivo
- SSL/TLS recomendado para produção

## Monitoramento

O container inclui health check que verifica:

- Disponibilidade da aplicação
- Endpoint `/api/health/` (você precisa implementar este endpoint)

## Backup

Para fazer backup do banco SQLite:

```bash
# Copiar o arquivo do banco
cp ./data/db.sqlite3 backup/db-$(date +%Y%m%d).sqlite3
```

## Troubleshooting

### Container não inicia

```bash
# Verificar logs
docker-compose logs web

# Verificar se as portas estão disponíveis
netstat -tulpn | grep 8000
```

### Problemas de permissão

```bash
# Ajustar permissões dos volumes
sudo chown -R 1000:1000 ./data
sudo chown -R 1000:1000 ./staticfiles
```

### Problemas de conectividade

- Verificar se o token do GitLab está correto
- Verificar se a URL do GitLab está acessível
- Verificar configurações de firewall
