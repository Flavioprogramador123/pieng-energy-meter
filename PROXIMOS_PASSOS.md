# ✅ Próximos Passos - Implementação PIENG

> **Status**: 📋 Plano de ação definido  
> **Data**: 18/10/2025  
> **Objetivo**: Implementar sistema multi-tenant de monitoramento energético

---

## 🎯 Resumo da Estratégia

Você está criando um **SaaS de monitoramento energético** onde:
- ✅ Cada cliente terá acesso **apenas aos seus dispositivos** (portal isolado)
- ✅ Você **cobra mensalmente** pelo monitoramento (R$ 297-1.497)
- ✅ Oferece **consultoria especializada** para economia de energia
- ✅ Sistema **independente** de terceiros (dados no seu Fidelco)
- ✅ Usa **tecnologias robustas** (PostgreSQL, Node.js, Python, React)

---

## 📋 Checklist de Implementação

### **Fase 1: Preparação da Infraestrutura** ⏱️ Esta Semana

#### ✅ **Passo 1: Configurar Fidelco** (2-3 horas)
**O que fazer**:
```bash
# 1. Conectar no Fidelco via SSH
ssh seu-usuario@IP_DO_FIDELCO

# 2. Baixar e executar script de setup
wget https://raw.githubusercontent.com/.../setup_fidelco.sh
chmod +x setup_fidelco.sh
sudo ./setup_fidelco.sh

# 3. Aguardar conclusão (15-30 minutos)
# O script instala: PostgreSQL, Redis, Docker, Node.js, Python
```

**Resultado esperado**:
- ✅ PostgreSQL 16 rodando na porta 5432
- ✅ Redis rodando na porta 6379
- ✅ Firewall configurado
- ✅ Backups automáticos habilitados

**Validação**:
```bash
# Testar PostgreSQL
psql -h localhost -U pieng_admin -d pieng_production

# Testar Redis
redis-cli ping

# Ver serviços rodando
systemctl status postgresql redis-server
```

---

#### ✅ **Passo 2: Configurar Acesso Remoto Seguro** (1 hora)

**Opção A: VPN WireGuard (Recomendado)**
```bash
# No Fidelco
sudo apt install wireguard
# Seguir instruções em SETUP_FIDELCO.md seção "Configurar VPN"
```

**Opção B: Túnel SSH (Mais simples para testes)**
```bash
# No seu computador
ssh -L 5432:localhost:5432 -L 6379:localhost:6379 usuario@IP_FIDELCO -N

# Deixar rodando em segundo plano
# Agora você pode acessar PostgreSQL em localhost:5432
```

**Opção C: Supabase como proxy** (Temporário)
- Já tem Supabase configurado
- Pode usar como backup enquanto testa Fidelco

**Validação**:
```bash
# No seu computador, testar conexão
psql -h localhost -U pieng_admin -d pieng_production
# (Se usar túnel SSH, conectará no Fidelco)
```

---

#### ✅ **Passo 3: Criar Schema Multi-Tenant** (30 minutos)

```bash
# Conectar no PostgreSQL do Fidelco
psql -h IP_FIDELCO -U pieng_admin -d pieng_production

# Copiar e colar o SQL completo de ANALISE_COMPLETA_SISTEMAS.md
# Seção: "1.2. Criar Schema Multi-Tenant Unificado"
```

**Validação**:
```sql
-- Ver tabelas criadas
\dt

-- Deve mostrar:
-- clients, users, devices, measurements, alarm_rules, alarm_events, etc

-- Testar inserindo cliente de teste
INSERT INTO clients (name, subdomain, subscription_plan, monthly_fee) 
VALUES ('Cliente Teste', 'teste', 'basic', 297.00);

SELECT * FROM clients;
```

---

### **Fase 2: Adaptar Código Existente** ⏱️ Semana 1-2

#### ✅ **Passo 4: Adaptar Energy Meter para Multi-Tenant** (2-3 dias)

**Localização**: `C:\Users\flavi\projeto\pieng-energy-meter`

**Modificações necessárias**:

1. **Atualizar configuração do banco**
```python
# app/core/config.py
class Settings(BaseSettings):
    app_name: str = "Energy Meter Master"
    api_prefix: str = "/api"
    # MUDAR de SQLite para PostgreSQL
    database_url: str = "postgresql://pieng_admin:senha@IP_FIDELCO:5432/pieng_production"
    # ... resto
```

2. **Adicionar middleware de tenant**
```python
# app/middleware/tenant.py
# Copiar código da seção "2.1. Adaptar Energy Meter" em ANALISE_COMPLETA_SISTEMAS.md
```

3. **Atualizar models.py**
```python
# app/models.py
# Já tem Client, Device, Measurement
# Apenas garantir que todas as queries filtrem por client_id
```

4. **Testar localmente**
```bash
cd C:\Users\flavi\projeto\pieng-energy-meter

# Ativar venv
.venv\Scripts\activate

# Atualizar .env com nova DATABASE_URL
echo DATABASE_URL=postgresql://pieng_admin:senha@localhost:5432/pieng_production >> .env

# Rodar migrations
# (Se necessário, ajustar SQLAlchemy para PostgreSQL)

# Iniciar servidor
uvicorn app.main:app --reload
```

**Validação**:
- [ ] API inicia sem erros
- [ ] Consegue listar clientes
- [ ] Consegue criar dispositivo
- [ ] Medições são salvas no PostgreSQL

---

#### ✅ **Passo 5: Adicionar Isolamento por Cliente na API** (1-2 dias)

```python
# Em todos os endpoints, adicionar verificação de client_id

# Exemplo: app/routers/devices.py
@router.get("/devices")
def list_devices(
    request: Request,
    db: Session = Depends(get_db)
):
    # Pegar client_id do token JWT ou header
    client_id = request.state.client_id
    
    # Filtrar apenas dispositivos deste cliente
    devices = crud.list_devices(db, client_id=client_id)
    return devices

# Aplicar em TODOS os endpoints:
# - /devices
# - /metrics
# - /alarms
# - /dashboard
```

**Validação**:
- [ ] Usuário do Cliente A não vê dados do Cliente B
- [ ] Admin vê todos os dados
- [ ] Teste com 2 clientes diferentes

---

#### ✅ **Passo 6: Atualizar Frontend React (PIENG PostgreSQL)** (2-3 dias)

**Localização**: `C:\Users\flavi\projeto\pieng_postgres\frontend`

**Criar página de portal do cliente**:
```bash
cd C:\Users\flavi\projeto\pieng_postgres\frontend

# Criar nova página
# src/pages/ClientPortal.tsx
# Copiar código da seção "3.1. Portal Cliente" em ANALISE_COMPLETA_SISTEMAS.md

# Adicionar rota
# src/App.tsx
<Route path="/portal" element={<ClientPortal />} />
```

**Validação**:
- [ ] Cliente consegue fazer login
- [ ] Vê apenas seus dispositivos
- [ ] Dashboard mostra consumo correto
- [ ] Gráficos carregam

---

### **Fase 3: Testar com Cliente Real** ⏱️ Semana 3

#### ✅ **Passo 7: Cadastrar Primeiro Cliente Piloto** (1 dia)

```sql
-- No PostgreSQL
INSERT INTO clients (name, subdomain, subscription_plan, monthly_fee) 
VALUES ('Empresa XYZ', 'xyz', 'professional', 597.00);

-- Criar usuário para esse cliente
INSERT INTO users (client_id, email, name, password_hash, role)
VALUES (
    1, -- id do cliente
    'admin@empresaxyz.com',
    'Administrador XYZ',
    '$2b$12$...',  -- Hash bcrypt da senha
    'client_admin'
);

-- Cadastrar dispositivo do cliente
INSERT INTO devices (client_id, name, device_type, config, active)
VALUES (
    1,
    'Medidor Principal',
    'modbus_tcp',
    '{"host": "10.0.0.109", "port": 8899, "slave_id": 1, "driver": "sdm630"}',
    true
);
```

**Configurar hardware**:
```bash
# Se for SDM630 via EW11
# 1. Configurar IP do EW11: 10.0.0.109
# 2. Porta: 8899
# 3. Slave ID: 1
# 4. Testar comunicação
```

**Validação**:
- [ ] Cliente consegue logar
- [ ] Vê seu dispositivo
- [ ] Recebe medições em tempo real
- [ ] Alarmes funcionam

---

#### ✅ **Passo 8: Configurar Cobrança Recorrente** (1 dia)

**Opções**:

**Opção A: Integração Stripe** (Recomendado)
```bash
npm install stripe

# Criar produtos e preços no Stripe
# Implementar webhook para renovação automática
```

**Opção B: Integração PagSeguro/MercadoPago** (Brasil)
```bash
npm install mercadopago

# Configurar assinatura recorrente
```

**Opção C: Manual (para começar)**
- Enviar link de pagamento mensal por email
- Marcar manualmente no banco quem pagou
- Bloquear acesso de inadimplentes

```sql
-- Adicionar campo de status de assinatura
ALTER TABLE clients ADD COLUMN payment_status VARCHAR(50) DEFAULT 'active';
-- active, pending, suspended, cancelled

-- Criar view de clientes inadimplentes
CREATE VIEW clients_overdue AS
SELECT * FROM clients 
WHERE payment_status = 'pending' 
AND updated_at < NOW() - INTERVAL '30 days';
```

---

### **Fase 4: Melhorias e Otimizações** ⏱️ Semana 4+

#### ✅ **Passo 9: Implementar Análises de Economia** (2-3 dias)

```typescript
// backend/src/services/energy-analysis.service.ts
export class EnergyAnalysisService {
  async analyzeClientEnergy(clientId: number, period: string) {
    // 1. Buscar consumo do período
    const measurements = await this.getMeasurements(clientId, period);
    
    // 2. Calcular pico vs fora-ponta
    const peakConsumption = this.calculatePeakConsumption(measurements);
    
    // 3. Identificar desperdícios
    const waste = this.identifyWaste(measurements);
    
    // 4. Calcular economia potencial
    const savings = this.calculateSavings(waste);
    
    // 5. Gerar recomendações
    const recommendations = this.generateRecommendations(savings);
    
    return {
      totalConsumption,
      peakConsumption,
      waste,
      potentialSavings: savings,
      recommendations
    };
  }
}
```

**Validação**:
- [ ] Relatório de economia gerado
- [ ] Recomendações personalizadas
- [ ] Cliente consegue baixar PDF

---

#### ✅ **Passo 10: Sistema de Notificações** (1-2 dias)

**WhatsApp Business API** (Recomendado)
```bash
npm install whatsapp-web.js

# Configurar webhook para alarmes
# Enviar mensagem quando alarme dispara
```

**Email** (Mais simples)
```bash
npm install nodemailer

# Usar Google Workspace SMTP
# Enviar email quando:
# - Alarme dispara
# - Consumo ultrapassa threshold
# - Relatório mensal pronto
```

**SMS** (Opcional)
```bash
npm install twilio

# Para alarmes críticos
```

---

### **Fase 5: Deploy em Produção** ⏱️ Semana 5

#### ✅ **Passo 11: Deploy Backend no Fidelco** (1 dia)

```bash
# No Fidelco
cd /opt/pieng

# Clonar repositórios
git clone https://github.com/seu-usuario/pieng-energy-meter.git backend-python
git clone https://github.com/seu-usuario/pieng_postgres.git backend-node

# Configurar e iniciar com PM2
# (Scripts fornecidos em SETUP_FIDELCO.md)
```

---

#### ✅ **Passo 12: Deploy Frontend no Vercel** (30 minutos)

```bash
# No projeto frontend
cd C:\Users\flavi\projeto\pieng_postgres\frontend

# Login no Vercel
npm i -g vercel
vercel login

# Deploy
vercel --prod

# Configurar variáveis de ambiente no Vercel
VITE_API_URL=https://api.seu-dominio.com
```

**Resultado**: Frontend acessível em `https://seu-app.vercel.app`

---

#### ✅ **Passo 13: Configurar Domínio** (30 minutos)

**Comprar domínio** (ex: monitoramento-energia.com.br)

**Configurar DNS**:
```
@ A record → IP_DO_FIDELCO (backend)
api CNAME → seu-app.vercel.app (API)
app CNAME → seu-app.vercel.app (Frontend)
```

**Resultado**:
- Frontend: https://app.seu-dominio.com
- API: https://api.seu-dominio.com
- Subdomínios clientes: https://cliente-a.seu-dominio.com

---

## 🎯 Resumo das Prioridades

### **Esta Semana (Crítico)**
1. ⭐ Configurar Fidelco com PostgreSQL
2. ⭐ Criar schema multi-tenant
3. ⭐ Testar conexão remota

### **Semana 1-2 (Alto)**
4. 🔥 Adaptar Energy Meter para multi-tenant
5. 🔥 Adicionar isolamento por cliente
6. 🔥 Atualizar frontend React

### **Semana 3 (Médio)**
7. 📊 Cadastrar cliente piloto
8. 📊 Configurar cobrança
9. 📊 Testar com hardware real

### **Semana 4+ (Baixo)**
10. 💡 Análises de economia
11. 💡 Sistema de notificações
12. 💡 Relatórios automáticos

---

## 💰 Investimento Estimado

### **Custos Mensais**
- **Servidor Fidelco**: R$ 0 (já tem)
- **Domínio**: R$ 40/mês
- **Vercel Pro** (se precisar): R$ 100/mês
- **OpenAI API**: ~R$ 50-200/mês (conforme uso)
- **Google Workspace**: Já tem
- **Total**: ~R$ 190-340/mês

### **Ponto de Equilíbrio**
- Plano Basic (R$ 297/mês): **2 clientes** pagando
- Plano Pro (R$ 597/mês): **1 cliente** pagando
- Meta inicial: 5 clientes = R$ 1.485-2.985/mês

---

## 📞 Suporte e Dúvidas

### **Documentos de Referência**
1. `ANALISE_COMPLETA_SISTEMAS.md` - Visão geral e arquitetura
2. `SETUP_FIDELCO.md` - Configuração completa do servidor
3. `README.md` - Cada projeto
4. `SISTEMA_AVANCADO.md` - Features avançadas

### **Comandos Úteis**

**Ver logs do Fidelco**:
```bash
# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Redis
sudo tail -f /var/log/redis/redis-server.log

# Aplicações (PM2)
pm2 logs
```

**Reiniciar serviços**:
```bash
sudo systemctl restart postgresql
sudo systemctl restart redis-server
pm2 restart all
```

**Backup manual**:
```bash
/opt/pieng/backup_database.sh
```

---

## ✅ Checklist de Validação Final

Antes de lançar para clientes:

### **Técnico**
- [ ] Fidelco operacional 24/7
- [ ] Backup automático funcionando
- [ ] Monitoramento ativo (Grafana)
- [ ] SSL/HTTPS configurado
- [ ] Firewall protegendo portas
- [ ] VPN ou túnel seguro

### **Funcional**
- [ ] Login funcional para clientes
- [ ] Isolamento de dados testado
- [ ] Medições em tempo real
- [ ] Alarmes disparando
- [ ] Dashboard responsivo
- [ ] Relatórios gerados

### **Negócio**
- [ ] Preços definidos
- [ ] Contrato de serviço pronto
- [ ] Termos de uso e privacidade
- [ ] Forma de pagamento configurada
- [ ] Suporte técnico definido
- [ ] Material de vendas pronto

---

## 🚀 Começar Agora

**Primeira ação (hoje)**:
```bash
# 1. Conectar no Fidelco
ssh usuario@IP_FIDELCO

# 2. Baixar script de setup
wget https://raw.githubusercontent.com/.../setup_fidelco.sh

# 3. Executar
chmod +x setup_fidelco.sh
sudo ./setup_fidelco.sh

# 4. Aguardar 15-30 minutos
# 5. Validar instalação
systemctl status postgresql redis-server
```

**Segunda ação (amanhã)**:
- Criar schema multi-tenant no PostgreSQL
- Testar conexão do seu computador

**Terceira ação (próxima semana)**:
- Adaptar código do Energy Meter
- Testar com cliente piloto

---

**Lembre-se**: 
- ✅ Você já tem a infraestrutura (Supabase, Vercel, Google Workspace)
- ✅ O código base já está funcional
- ✅ Só precisa adaptar para multi-tenant
- ✅ Foco em **entregar valor** para o primeiro cliente

**Boa sorte! 🚀**

---

**Criado em**: 18/10/2025  
**Status**: 📋 Pronto para execução  
**Objetivo**: Sistema em produção em 4-5 semanas

