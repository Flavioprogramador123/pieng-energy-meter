# 🖥️ Setup Fidelco - Servidor Central PostgreSQL

> **Objetivo**: Configurar Fidelco com Debian 11 como servidor central robusto  
> **Data**: 18/10/2025  
> **Status**: 📋 Aguardando execução (mini PC / HD em casa ainda não provisionado)

> **Atualização 2026-09-09 (escritório):** enquanto o Fidelco/mini PC não existe, o teste
> de storage está no HD `K:\STORAGE` com **Postgres nativo 17** (não Docker).
> Ver `docs/SETUP_POSTGRES_NATIVO_K.md` e `CHANGELOG.md`. O `docker-compose.yml`
> do Energy Meter foi **preservado** para reutilizar neste setup no futuro.

---

## 📦 Hardware: Fidelco

### **Especificações Recomendadas**
- **CPU**: Mínimo 4 cores (Recomendado: 8 cores)
- **RAM**: Mínimo 8GB (Recomendado: 16GB+)
- **Storage**: SSD 256GB+ (Recomendado: 512GB NVMe)
- **Network**: Gigabit Ethernet
- **OS**: Debian 11 (Bullseye)

---

## 🚀 Script de Instalação Automática

### **1. Setup Inicial do Sistema**

Salve como `setup_fidelco.sh` e execute:

```bash
#!/bin/bash
# Setup completo do Fidelco para PIENG Energy Platform
# Execute como root ou com sudo

set -e  # Para em caso de erro

echo "======================================"
echo "  PIENG Fidelco Setup - Debian 11    "
echo "======================================"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função de log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
   log_error "Este script precisa ser executado como root (sudo)"
   exit 1
fi

# 1. Atualizar sistema
log_info "Atualizando sistema..."
apt update
apt upgrade -y

# 2. Instalar dependências base
log_info "Instalando dependências base..."
apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ufw \
    fail2ban \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# 3. Instalar PostgreSQL 16
log_info "Instalando PostgreSQL 16..."

# Adicionar repositório oficial PostgreSQL
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt update
apt install -y postgresql-16 postgresql-contrib-16 postgresql-16-pgvector

# 4. Configurar PostgreSQL para acesso remoto
log_info "Configurando PostgreSQL para acesso remoto..."

PG_VERSION=16
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"

# Backup dos arquivos originais
cp $PG_CONF ${PG_CONF}.backup
cp $PG_HBA ${PG_HBA}.backup

# Permitir conexões externas
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF

# Aumentar conexões simultâneas
sed -i "s/max_connections = 100/max_connections = 200/" $PG_CONF

# Otimizar para SSD
cat >> $PG_CONF << EOF

# PIENG Optimizations
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_parallel_maintenance_workers = 4
EOF

# Configurar autenticação
cat >> $PG_HBA << EOF

# PIENG Remote Access
host    all             all             0.0.0.0/0               scram-sha-256
host    all             all             ::/0                    scram-sha-256
EOF

# Reiniciar PostgreSQL
systemctl restart postgresql

# 5. Criar usuário e banco PIENG
log_info "Criando banco de dados PIENG..."

sudo -u postgres psql << EOF
-- Criar usuário PIENG
CREATE USER pieng_admin WITH PASSWORD 'CHANGE_THIS_PASSWORD';
ALTER USER pieng_admin WITH SUPERUSER;

-- Criar banco principal
CREATE DATABASE pieng_production OWNER pieng_admin;

-- Conectar e criar extensões
\c pieng_production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Criar banco de desenvolvimento
CREATE DATABASE pieng_development OWNER pieng_admin;

-- Criar banco de teste
CREATE DATABASE pieng_test OWNER pieng_admin;

\q
EOF

log_info "PostgreSQL configurado com sucesso!"

# 6. Instalar Redis
log_info "Instalando Redis..."
apt install -y redis-server

# Configurar Redis
cat > /etc/redis/redis.conf << EOF
bind 0.0.0.0
protected-mode yes
requirepass CHANGE_THIS_REDIS_PASSWORD
port 6379
tcp-backlog 511
timeout 0
tcp-keepalive 300
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis
maxmemory 1gb
maxmemory-policy allkeys-lru
EOF

systemctl restart redis-server
systemctl enable redis-server

log_info "Redis configurado com sucesso!"

# 7. Instalar Docker
log_info "Instalando Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Instalar Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

systemctl enable docker
systemctl start docker

log_info "Docker instalado com sucesso!"

# 8. Instalar Node.js 20 LTS
log_info "Instalando Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Instalar PM2 globalmente
npm install -g pm2
pm2 startup

log_info "Node.js e PM2 instalados!"

# 9. Instalar Python 3.11
log_info "Instalando Python 3.11..."
apt install -y python3.11 python3.11-venv python3-pip

log_info "Python 3.11 instalado!"

# 10. Configurar Firewall (UFW)
log_info "Configurando firewall..."
ufw --force enable
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw allow 5432/tcp    # PostgreSQL
ufw allow 6379/tcp    # Redis
ufw allow 3000/tcp    # Backend Node.js
ufw allow 8000/tcp    # Backend FastAPI

log_info "Firewall configurado!"

# 11. Configurar Fail2Ban
log_info "Configurando Fail2Ban..."
systemctl enable fail2ban
systemctl start fail2ban

# 12. Criar diretórios de trabalho
log_info "Criando estrutura de diretórios..."
mkdir -p /opt/pieng/{backend-node,backend-python,logs,backups,uploads}
chown -R $SUDO_USER:$SUDO_USER /opt/pieng

# 13. Criar script de backup automático
log_info "Configurando backup automático..."
cat > /opt/pieng/backup_database.sh << 'EOFBACKUP'
#!/bin/bash
# Backup automático do PostgreSQL

BACKUP_DIR="/opt/pieng/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pieng_backup_${DATE}.sql.gz"

# Criar backup
sudo -u postgres pg_dump pieng_production | gzip > $BACKUP_FILE

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "pieng_backup_*.sql.gz" -mtime +7 -delete

# Upload para Google Cloud Storage (se configurado)
# gsutil cp $BACKUP_FILE gs://pieng-backups/

echo "Backup criado: $BACKUP_FILE"
EOFBACKUP

chmod +x /opt/pieng/backup_database.sh

# Adicionar ao cron (diário às 2h da manhã)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/pieng/backup_database.sh") | crontab -

log_info "Backup automático configurado!"

# 14. Informações finais
echo ""
echo "======================================"
log_info "Setup concluído com sucesso!"
echo "======================================"
echo ""
echo -e "${YELLOW}IMPORTANTE - PRÓXIMOS PASSOS:${NC}"
echo ""
echo "1. Alterar senhas padrão:"
echo "   - PostgreSQL: sudo -u postgres psql -c \"ALTER USER pieng_admin PASSWORD 'nova_senha';\""
echo "   - Redis: editar /etc/redis/redis.conf"
echo ""
echo "2. Obter IP do servidor:"
echo "   - IP local: $(hostname -I | awk '{print $1}')"
echo "   - IP público: $(curl -s ifconfig.me)"
echo ""
echo "3. Testar conexão PostgreSQL:"
echo "   psql -h localhost -U pieng_admin -d pieng_production"
echo ""
echo "4. Testar Redis:"
echo "   redis-cli -a CHANGE_THIS_REDIS_PASSWORD ping"
echo ""
echo "5. Configurar VPN/Túnel SSH para acesso seguro remoto"
echo ""
echo "6. Atualizar .env dos projetos com:"
echo "   DATABASE_URL=postgresql://pieng_admin:senha@IP_FIDELCO:5432/pieng_production"
echo "   REDIS_URL=redis://:senha@IP_FIDELCO:6379"
echo ""
echo -e "${GREEN}Fidelco pronto para receber as aplicações PIENG!${NC}"
echo ""
```

### **2. Executar o Setup**

```bash
# No Fidelco (via SSH ou diretamente)
wget https://raw.githubusercontent.com/seu-repo/pieng/main/setup_fidelco.sh
chmod +x setup_fidelco.sh
sudo ./setup_fidelco.sh
```

---

## 🔐 Configuração de Segurança Avançada

### **1. Alterar Senhas Padrão**

```bash
# PostgreSQL
sudo -u postgres psql
ALTER USER pieng_admin PASSWORD 'SUA_SENHA_SUPER_FORTE_AQUI';
\q

# Redis
sudo nano /etc/redis/redis.conf
# Alterar linha: requirepass SUA_SENHA_REDIS_AQUI
sudo systemctl restart redis-server
```

### **2. Configurar Certificado SSL (Let's Encrypt)**

```bash
# Instalar Certbot
sudo apt install -y certbot

# Obter certificado (se tiver domínio)
sudo certbot certonly --standalone -d seu-dominio.com

# Configurar PostgreSQL com SSL
sudo nano /etc/postgresql/16/main/postgresql.conf
# Adicionar:
# ssl = on
# ssl_cert_file = '/etc/letsencrypt/live/seu-dominio.com/fullchain.pem'
# ssl_key_file = '/etc/letsencrypt/live/seu-dominio.com/privkey.pem'

sudo systemctl restart postgresql
```

### **3. Configurar VPN (WireGuard) - RECOMENDADO**

```bash
# Instalar WireGuard
sudo apt install -y wireguard

# Gerar chaves
wg genkey | sudo tee /etc/wireguard/privatekey | wg pubkey | sudo tee /etc/wireguard/publickey

# Configurar servidor
sudo nano /etc/wireguard/wg0.conf
```

Conteúdo do arquivo:
```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = CHAVE_PRIVADA_DO_SERVIDOR

# Cliente 1 (seu computador de desenvolvimento)
[Peer]
PublicKey = CHAVE_PUBLICA_CLIENTE_1
AllowedIPs = 10.0.0.2/32

# Cliente 2 (outro desenvolvedor)
[Peer]
PublicKey = CHAVE_PUBLICA_CLIENTE_2
AllowedIPs = 10.0.0.3/32
```

```bash
# Iniciar VPN
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0

# Permitir no firewall
sudo ufw allow 51820/udp
```

**No seu computador (cliente):**
```bash
# Instalar WireGuard
# Windows: baixar de wireguard.com
# Linux: sudo apt install wireguard

# Criar configuração cliente
# wg0-client.conf:
[Interface]
PrivateKey = SUA_CHAVE_PRIVADA
Address = 10.0.0.2/24

[Peer]
PublicKey = CHAVE_PUBLICA_DO_SERVIDOR
Endpoint = IP_PUBLICO_FIDELCO:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

---

## 📊 Monitoramento e Observabilidade

### **1. Instalar Prometheus + Grafana**

```bash
# Criar docker-compose.yml para monitoring
cat > /opt/pieng/docker-compose-monitoring.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: pieng_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: pieng_grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: pieng_postgres_exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://pieng_admin:senha@host.docker.internal:5432/pieng_production?sslmode=disable
    ports:
      - "9187:9187"
    restart: unless-stopped

  redis_exporter:
    image: oliver006/redis_exporter:latest
    container_name: pieng_redis_exporter
    environment:
      - REDIS_ADDR=redis://host.docker.internal:6379
      - REDIS_PASSWORD=SUA_SENHA_REDIS
    ports:
      - "9121:9121"
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
EOF

# Criar configuração Prometheus
mkdir -p /opt/pieng/prometheus
cat > /opt/pieng/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']

  - job_name: 'node_backend'
    static_configs:
      - targets: ['host.docker.internal:3000']

  - job_name: 'fastapi_backend'
    static_configs:
      - targets: ['host.docker.internal:8000']
EOF

# Iniciar serviços de monitoring
cd /opt/pieng
docker-compose -f docker-compose-monitoring.yml up -d
```

**Acessar**:
- Prometheus: `http://IP_FIDELCO:9090`
- Grafana: `http://IP_FIDELCO:3001` (admin/admin)

---

## 🚀 Deploy das Aplicações

### **1. Deploy Backend Node.js (PIENG PostgreSQL)**

```bash
# Clonar repositório
cd /opt/pieng/backend-node
git clone https://github.com/seu-usuario/pieng_postgres.git .

# Configurar variáveis
cat > .env << EOF
NODE_ENV=production
PORT=3000

# Database
DATABASE_URL=postgresql://pieng_admin:senha@localhost:5432/pieng_production

# Redis
REDIS_URL=redis://:senha@localhost:6379

# JWT
JWT_SECRET=$(openssl rand -base64 32)
JWT_REFRESH_SECRET=$(openssl rand -base64 32)

# Google Cloud (se usar)
GOOGLE_APPLICATION_CREDENTIALS=/opt/pieng/credentials/google-cloud-key.json

# OpenAI
OPENAI_API_KEY=sua-chave-aqui
EOF

# Instalar dependências
npm install

# Gerar Prisma Client
npx prisma generate

# Executar migrations
npx prisma migrate deploy

# Build
npm run build

# Iniciar com PM2
pm2 start npm --name "pieng-node" -- start
pm2 save
```

### **2. Deploy Backend Python (Energy Meter)**

```bash
# Clonar repositório
cd /opt/pieng/backend-python
git clone https://github.com/seu-usuario/pieng-energy-meter.git .

# Criar venv
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis
cat > .env << EOF
APP_NAME=Energy Meter Master
API_PREFIX=/api
DATABASE_URL=postgresql://pieng_admin:senha@localhost:5432/pieng_production
SCHEDULER_TIMEZONE=America/Sao_Paulo
ENABLE_FORWARDING=false
EOF

# Iniciar com PM2 (usando ecosystem)
pm2 start ecosystem.config.js
pm2 save
```

---

## 📈 Otimização de Performance PostgreSQL

### **1. Tuning Avançado**

```sql
-- Conectar como superuser
sudo -u postgres psql pieng_production

-- Configurar work_mem para queries complexas
ALTER SYSTEM SET work_mem = '16MB';

-- Configurar maintenance_work_mem
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- Habilitar parallel queries
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;

-- Configurar autovacuum agressivo
ALTER SYSTEM SET autovacuum_max_workers = 4;
ALTER SYSTEM SET autovacuum_naptime = '30s';

-- Aplicar mudanças
SELECT pg_reload_conf();
```

### **2. Criar Índices Otimizados**

```sql
-- Índices para medições (time-series)
CREATE INDEX CONCURRENTLY idx_measurements_device_time 
    ON measurements(device_id, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_measurements_metric_time 
    ON measurements(metric, timestamp DESC) 
    WHERE client_id IS NOT NULL;

-- Índice parcial para alarmes ativos
CREATE INDEX CONCURRENTLY idx_alarm_events_unacknowledged 
    ON alarm_events(client_id, timestamp DESC) 
    WHERE acknowledged = false;

-- Índice para busca full-text (se necessário)
CREATE INDEX CONCURRENTLY idx_devices_name_trgm 
    ON devices USING gin(name gin_trgm_ops);
```

### **3. Particionamento de Tabela de Medições**

```sql
-- Criar tabela particionada
CREATE TABLE measurements_partitioned (
    LIKE measurements INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Criar partições mensais
CREATE TABLE measurements_2025_10 PARTITION OF measurements_partitioned
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE measurements_2025_11 PARTITION OF measurements_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Script para criar automaticamente partições futuras
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'measurements_' || to_char(start_date, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF measurements_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;

-- Agendar criação automática (via pg_cron ou cron externo)
```

---

## 🔄 Backup e Recuperação

### **1. Backup Completo Diário**

Já configurado no script principal, mas aqui estão comandos manuais:

```bash
# Backup completo
sudo -u postgres pg_dump pieng_production | gzip > /opt/pieng/backups/manual_backup_$(date +%Y%m%d).sql.gz

# Backup apenas schema
sudo -u postgres pg_dump -s pieng_production > /opt/pieng/backups/schema_$(date +%Y%m%d).sql

# Backup de uma tabela específica
sudo -u postgres pg_dump -t measurements pieng_production | gzip > /opt/pieng/backups/measurements_$(date +%Y%m%d).sql.gz
```

### **2. Restauração**

```bash
# Restaurar backup completo
gunzip -c /opt/pieng/backups/backup.sql.gz | sudo -u postgres psql pieng_production

# Restaurar em novo banco
sudo -u postgres createdb pieng_restored
gunzip -c /opt/pieng/backups/backup.sql.gz | sudo -u postgres psql pieng_restored
```

### **3. Sincronização com Google Cloud Storage**

```bash
# Instalar gsutil
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Upload automático de backups
cat >> /opt/pieng/backup_database.sh << 'EOF'

# Após criar backup local
if command -v gsutil &> /dev/null; then
    gsutil cp $BACKUP_FILE gs://pieng-backups/postgresql/
    echo "Backup enviado para Google Cloud Storage"
fi
EOF
```

---

## 📊 Checklist de Validação

Após executar o setup, validar:

### **Sistema Operacional**
- [ ] Debian 11 atualizado
- [ ] Firewall (UFW) ativo
- [ ] Fail2Ban ativo
- [ ] SSH configurado (trocar porta padrão)

### **Banco de Dados**
- [ ] PostgreSQL 16 rodando
- [ ] Acesso remoto funcionando
- [ ] Bancos criados (production, development, test)
- [ ] Backups automáticos configurados
- [ ] Extensões instaladas (uuid-ossp, pg_trgm, vector)

### **Cache**
- [ ] Redis rodando
- [ ] Senha configurada
- [ ] Persistência habilitada

### **Aplicações**
- [ ] Node.js 20 instalado
- [ ] Python 3.11 instalado
- [ ] PM2 configurado com auto-start
- [ ] Docker funcionando

### **Monitoramento**
- [ ] Prometheus coletando métricas
- [ ] Grafana acessível
- [ ] Exporters funcionando (PostgreSQL, Redis)

### **Segurança**
- [ ] Todas as senhas padrão alteradas
- [ ] VPN configurada (opcional mas recomendado)
- [ ] SSL/TLS configurado
- [ ] Logs de auditoria ativos

### **Backup**
- [ ] Script de backup funcionando
- [ ] Cron job configurado
- [ ] Upload para cloud (se aplicável)
- [ ] Restauração testada

---

## 🆘 Troubleshooting

### **PostgreSQL não aceita conexões remotas**

```bash
# Verificar se está ouvindo em todas as interfaces
sudo netstat -plnt | grep 5432

# Verificar logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Testar conexão local
psql -h localhost -U pieng_admin -d pieng_production

# Testar de outra máquina
psql -h IP_FIDELCO -U pieng_admin -d pieng_production
```

### **Redis não conecta**

```bash
# Verificar status
sudo systemctl status redis-server

# Testar conexão
redis-cli -a sua_senha ping

# Verificar logs
sudo tail -f /var/log/redis/redis-server.log
```

### **Aplicação não inicia com PM2**

```bash
# Ver logs
pm2 logs

# Reiniciar aplicação
pm2 restart pieng-node

# Ver status detalhado
pm2 show pieng-node

# Limpar e reiniciar
pm2 delete all
pm2 start ecosystem.config.js
```

---

## 📞 Suporte

**Documentação Relacionada**:
- `ANALISE_COMPLETA_SISTEMAS.md` - Visão geral da arquitetura
- `REMOTE_ACCESS.md` - Configuração de acesso remoto
- PostgreSQL Docs: https://www.postgresql.org/docs/16/

**Comandos Úteis**:
```bash
# Status de todos os serviços
systemctl status postgresql redis-server docker

# Monitorar recursos
htop

# Ver conexões PostgreSQL ativas
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Ver uso de espaço do banco
sudo -u postgres psql pieng_production -c "SELECT pg_size_pretty(pg_database_size('pieng_production'));"
```

---

**Criado em**: 18/10/2025  
**Versão**: 1.0  
**Status**: 📋 Pronto para execução

