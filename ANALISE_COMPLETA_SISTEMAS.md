# 📊 Análise Completa dos Sistemas - Convergência PIENG

> **Data**: 18/10/2025  
> **Objetivo**: Criar ecossistema integrado de monitoramento energético e gestão de ativos  
> **Modelo de Negócio**: SaaS multi-tenant com consultoria especializada

---

## 🎯 Visão Estratégica do Negócio

### **Proposta de Valor**
Sistema completo de monitoramento energético com:
- **Independência** de plataformas terceiras
- **Análises proprietárias** e alarmes personalizados
- **Portal cliente** white-label (cada cliente acessa apenas sua planta)
- **Modelo SaaS**: Receita recorrente mensal por monitoramento + consultoria
- **Consultoria especializada**: Mitigação de gastos energéticos

### **Infraestrutura Disponível**
- ✅ **Servidor Fidelco** com Debian 11 (banco robusto central)
- ✅ **Supabase** (PostgreSQL gerenciado + Auth)
- ✅ **Vercel** (deploy frontend)
- ✅ **Netlify** (alternativa frontend)
- ✅ **Google Workspace Pro** (emails, drive, colaboração)
- ✅ **Google Cloud APIs** (pagas) - Firebase, BigQuery, Vertex AI
- ✅ **Budget**: APIs pagas disponíveis para expansão

---

## 📦 Inventário dos Sistemas

### **Sistema 1: PIENG Energy Meter (SQLite)**
**Localização**: `C:\Users\flavi\projeto\pieng-energy-meter`

#### **Características**
- **Stack**: Python + FastAPI + SQLAlchemy
- **Banco**: SQLite (local)
- **Frontend**: Jinja2 + Chart.js
- **Foco**: Monitoramento de medidores Modbus (PZEM-004T, SDM630)
- **Deploy**: Vercel (serverless)

#### **Pontos Fortes**
- ✅ Leve e rápido para prototipagem
- ✅ Drivers Modbus RTU/TCP funcionais
- ✅ Analytics básico (Six Sigma, regressão)
- ✅ Sistema de alarmes configurável
- ✅ Pronto para Vercel

#### **Limitações**
- ⚠️ SQLite não suporta multi-tenant robusto
- ⚠️ Sem autenticação real
- ⚠️ Polling limitado em serverless
- ⚠️ Sem portal cliente isolado

---

### **Sistema 2: PIENG PostgreSQL (Enterprise)**
**Localização**: `C:\Users\flavi\projeto\pieng_postgres`

#### **Características**
- **Stack**: Node.js + Express + TypeScript + React
- **Banco**: PostgreSQL + Redis
- **Frontend**: React + Vite + Tailwind
- **Foco**: Gestão completa de ativos + IoT + IA + Drones

#### **Pontos Fortes**
- ✅ Arquitetura enterprise-grade
- ✅ PostgreSQL robusto (multi-tenant ready)
- ✅ Autenticação completa (JWT + MFA)
- ✅ RBAC (Role-Based Access Control)
- ✅ Sistema RAG com IA
- ✅ Módulo financeiro
- ✅ Docker + CI/CD

#### **Diferenciais Avançados**
- ✅ Sistema de drones autônomos
- ✅ OCR inteligente
- ✅ Calculadora solar
- ✅ Base de conhecimento (RAG)
- ✅ Gestão de ativos com QR Code

---

## 🔄 Estratégia de Convergência

### **Arquitetura Proposta: Híbrida Multi-Camada**

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE CLIENTES                       │
│                                                             │
│  Cliente A       Cliente B       Cliente C    ...          │
│  (acesso web)    (acesso web)    (acesso web)             │
│  dashboard       dashboard       dashboard                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE APRESENTAÇÃO (Frontend)              │
│                                                             │
│  ┌─────────────────────┐      ┌─────────────────────┐     │
│  │  React Multi-Tenant │      │  Admin Dashboard    │     │
│  │  (Vercel/Netlify)   │      │  (Gestão Completa)  │     │
│  └─────────────────────┘      └─────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               CAMADA DE API GATEWAY                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Traefik / Nginx                                     │  │
│  │  - Rate limiting                                     │  │
│  │  - Auth validation                                   │  │
│  │  - Load balancing                                    │  │
│  │  - SSL termination                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE APLICAÇÃO (Backend)                  │
│                                                             │
│  ┌─────────────────────┐      ┌─────────────────────┐     │
│  │  FastAPI Service    │      │  Node.js Service    │     │
│  │  (Energy Monitor)   │      │  (Asset Management) │     │
│  │  - Modbus drivers   │      │  - IA/RAG           │     │
│  │  - Analytics        │      │  - Financeiro       │     │
│  │  - Alarmes          │      │  - Drones           │     │
│  └─────────────────────┘      └─────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE DADOS (Fidelco + Cloud)              │
│                                                             │
│  ┌────────────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │  PostgreSQL    │  │   Redis    │  │   Supabase      │  │
│  │  (Fidelco      │  │  (Cache)   │  │   (Backup/Sync) │  │
│  │   Debian 11)   │  │            │  │                 │  │
│  │  - Master DB   │  └────────────┘  └─────────────────┘  │
│  │  - Multi-tenant│                                        │
│  │  - Séries temp.│  ┌────────────────────────────────┐   │
│  │                │  │  Google Cloud Storage          │   │
│  │                │  │  - Backups                     │   │
│  │                │  │  - Documentos OCR              │   │
│  └────────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE DISPOSITIVOS IoT                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PZEM-004T   │  │   SDM630     │  │  Sensores    │     │
│  │  (Modbus RTU)│  │  (Modbus TCP)│  │  Diversos    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Gateway EW11│  │  Drones      │  │  Câmeras     │     │
│  │  (RS485→WiFi)│  │  (Inspeção)  │  │  Térmicas    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Plano de Integração Técnica

### **Fase 1: Preparação da Infraestrutura (1-2 semanas)**

#### **1.1. Configurar Fidelco (Debian 11)**
```bash
# No servidor Fidelco
sudo apt update && sudo apt upgrade -y

# Instalar PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib

# Configurar para acesso remoto
sudo nano /etc/postgresql/16/main/postgresql.conf
# Alterar: listen_addresses = '*'

sudo nano /etc/postgresql/16/main/pg_hba.conf
# Adicionar: host all all 0.0.0.0/0 md5

# Instalar Redis
sudo apt install -y redis-server
sudo systemctl enable redis-server

# Instalar Docker (opcional, mas recomendado)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

#### **1.2. Criar Schema Multi-Tenant Unificado**
```sql
-- Estrutura multi-tenant com isolamento por cliente

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    subdomain VARCHAR(50) UNIQUE, -- cliente-a.seu-dominio.com
    external_id VARCHAR(200) UNIQUE,
    subscription_status VARCHAR(50) DEFAULT 'active', -- active, suspended, cancelled
    subscription_plan VARCHAR(50) DEFAULT 'basic', -- basic, pro, enterprise
    monthly_fee DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user', -- user, admin, technician, client_admin
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    device_type VARCHAR(50) NOT NULL, -- modbus_tcp, modbus_rtu, sensor, solar_panel
    active BOOLEAN DEFAULT true,
    config JSONB, -- Configuração específica do dispositivo
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    location_address TEXT,
    qr_code VARCHAR(255) UNIQUE, -- Para gestão de ativos
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE measurements (
    id BIGSERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE, -- Desnormalização para queries rápidas
    timestamp TIMESTAMP DEFAULT NOW(),
    metric VARCHAR(100) NOT NULL, -- voltage, current, power, energy_kwh, etc
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(50),
    extra JSONB
);

-- Índices otimizados para séries temporais
CREATE INDEX idx_measurements_device_metric_time 
    ON measurements(device_id, metric, timestamp DESC);

CREATE INDEX idx_measurements_client_time 
    ON measurements(client_id, timestamp DESC);

-- Particionamento por data (opcional, mas recomendado)
-- Para melhor performance com grandes volumes

CREATE TABLE alarm_rules (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    device_id INTEGER REFERENCES devices(id),
    name VARCHAR(200) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    operator VARCHAR(10) NOT NULL, -- >, <, >=, <=, ==, !=
    threshold DOUBLE PRECISION NOT NULL,
    severity VARCHAR(50) DEFAULT 'warning', -- info, warning, critical
    enabled BOOLEAN DEFAULT true,
    notification_channels JSONB, -- {email: true, sms: false, whatsapp: true}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE alarm_events (
    id BIGSERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alarm_rules(id) ON DELETE CASCADE,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    device_id INTEGER REFERENCES devices(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    metric VARCHAR(100),
    value DOUBLE PRECISION,
    details JSONB,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by INTEGER REFERENCES users(id),
    acknowledged_at TIMESTAMP
);

-- Tabela de consultoria e interações
CREATE TABLE consultations (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    consultant_id INTEGER REFERENCES users(id),
    type VARCHAR(50), -- analysis, optimization, emergency
    title VARCHAR(255),
    description TEXT,
    recommendations TEXT,
    expected_savings DECIMAL(10,2), -- R$ economia estimada
    status VARCHAR(50) DEFAULT 'open', -- open, in_progress, completed
    scheduled_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de análises de economia
CREATE TABLE energy_analysis (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    period_start DATE,
    period_end DATE,
    total_consumption_kwh DECIMAL(12,2),
    average_cost_per_kwh DECIMAL(10,4),
    total_cost DECIMAL(10,2),
    potential_savings DECIMAL(10,2),
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices adicionais
CREATE INDEX idx_devices_client ON devices(client_id);
CREATE INDEX idx_alarm_events_client_time ON alarm_events(client_id, timestamp DESC);
CREATE INDEX idx_users_client ON users(client_id);
```

### **Fase 2: Migração e Adaptação dos Sistemas (2-3 semanas)**

#### **2.1. Adaptar Energy Meter (FastAPI) para Multi-Tenant**
```python
# app/middleware/tenant.py
from fastapi import Request, HTTPException
from app.core.db import get_db
from app import crud

async def tenant_middleware(request: Request, call_next):
    """Identifica o cliente pela subdomain ou header"""
    # Opção 1: Por subdomain (cliente-a.seu-dominio.com)
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if "." in host else None
    
    # Opção 2: Por header customizado (para testes)
    client_id = request.headers.get("X-Client-ID")
    
    # Opção 3: Por token JWT (extrair client_id do token)
    auth_header = request.headers.get("authorization")
    
    if client_id:
        db = next(get_db())
        client = crud.get_client_by_id(db, int(client_id))
        if not client:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        request.state.client_id = client.id
        request.state.client = client
    
    response = await call_next(request)
    return response

# Adicionar no main.py
app.middleware("http")(tenant_middleware)
```

```python
# Modificar CRUD para sempre filtrar por client_id
def list_devices(db: Session, client_id: int):
    return db.query(Device).filter(Device.client_id == client_id).all()

def create_measurement(db: Session, measurement: MeasurementCreate, client_id: int):
    db_measurement = Measurement(
        **measurement.dict(),
        client_id=client_id  # Garantir isolamento
    )
    db.add(db_measurement)
    db.commit()
    return db_measurement
```

#### **2.2. Adaptar PostgreSQL System para Integração**
```typescript
// backend/src/middleware/energy-integration.middleware.ts
import { Request, Response, NextFunction } from 'express';
import axios from 'axios';

/**
 * Middleware para integrar com o Energy Meter Service (FastAPI)
 */
export const energyIntegrationMiddleware = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  // Adicionar client_id ao contexto
  req.clientId = req.user?.clientId;
  next();
};

// backend/src/services/energy-monitor.service.ts
import axios from 'axios';

export class EnergyMonitorService {
  private fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';

  /**
   * Buscar medições do Energy Meter
   */
  async getMeasurements(clientId: number, deviceId: number, metric?: string) {
    const response = await axios.get(`${this.fastApiUrl}/api/metrics`, {
      params: { device_id: deviceId, metric },
      headers: { 'X-Client-ID': clientId.toString() }
    });
    return response.data;
  }

  /**
   * Criar alarme no Energy Meter
   */
  async createAlarm(clientId: number, alarmRule: any) {
    const response = await axios.post(
      `${this.fastApiUrl}/api/alarms/rules`,
      alarmRule,
      { headers: { 'X-Client-ID': clientId.toString() } }
    );
    return response.data;
  }

  /**
   * Disparar análise de economia
   */
  async analyzeEnergySavings(clientId: number, period: { start: Date, end: Date }) {
    // Buscar dados de consumo
    const devices = await this.getClientDevices(clientId);
    
    let totalConsumption = 0;
    for (const device of devices) {
      const measurements = await this.getMeasurements(
        clientId, 
        device.id, 
        'energy_kwh'
      );
      // Calcular consumo do período...
    }

    // Algoritmo de análise de economia
    const analysis = {
      totalConsumption,
      averageCostPerKwh: 0.65, // R$ por kWh (ajustar por região)
      potentialSavings: this.calculatePotentialSavings(totalConsumption),
      recommendations: this.generateRecommendations(totalConsumption)
    };

    return analysis;
  }

  private calculatePotentialSavings(consumption: number): number {
    // Algoritmo proprietário de economia
    // Exemplo: detectar desperdício por horário de ponta
    return consumption * 0.15; // 15% de economia estimada
  }

  private generateRecommendations(consumption: number): string[] {
    const recommendations = [];
    
    if (consumption > 1000) {
      recommendations.push("Migrar cargas para horário fora-ponta");
      recommendations.push("Avaliar instalação de sistema solar fotovoltaico");
    }
    
    recommendations.push("Implementar sistema de gerenciamento de energia");
    return recommendations;
  }
}
```

### **Fase 3: Frontend Multi-Tenant (2-3 semanas)**

#### **3.1. Portal Cliente (React)**
```typescript
// frontend/src/pages/ClientDashboard.tsx
import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';

interface ClientDashboard {
  totalDevices: number;
  activeDevices: number;
  currentConsumption: number;
  monthlyConsumption: number;
  monthlyCost: number;
  alarms: Alarm[];
  recentMeasurements: Measurement[];
}

export const ClientDashboard = () => {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<ClientDashboard | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      // API retorna apenas dados do cliente autenticado
      const response = await api.get('/api/client/dashboard');
      setDashboard(response.data);
    } catch (error) {
      console.error('Erro ao carregar dashboard', error);
    }
  };

  if (!dashboard) return <div>Carregando...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">
        Bem-vindo, {user?.name}
      </h1>

      {/* Cards de resumo */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card title="Dispositivos Ativos" value={dashboard.activeDevices} />
        <Card title="Consumo Atual" value={`${dashboard.currentConsumption} kW`} />
        <Card title="Consumo Mensal" value={`${dashboard.monthlyConsumption} kWh`} />
        <Card title="Custo Mensal" value={`R$ ${dashboard.monthlyCost.toFixed(2)}`} />
      </div>

      {/* Gráfico de consumo */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Consumo nas Últimas 24h</h2>
        <ConsumptionChart data={dashboard.recentMeasurements} />
      </div>

      {/* Alarmes ativos */}
      {dashboard.alarms.length > 0 && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
          <h3 className="font-bold text-red-800">Alarmes Ativos</h3>
          <ul className="mt-2">
            {dashboard.alarms.map(alarm => (
              <li key={alarm.id} className="text-red-700">
                {alarm.name}: {alarm.details}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Lista de dispositivos */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Seus Dispositivos</h2>
        <DeviceList clientId={user?.clientId} />
      </div>
    </div>
  );
};
```

#### **3.2. Isolamento de Rotas por Cliente**
```typescript
// backend/src/routes/client-portal.routes.ts
import { Router } from 'express';
import { authMiddleware } from '../middlewares/auth.middleware';
import { clientOnlyMiddleware } from '../middlewares/client-only.middleware';

const router = Router();

// Middleware que garante que usuários só vejam seus próprios dados
const clientOnlyMiddleware = (req, res, next) => {
  const userClientId = req.user.clientId;
  const requestedClientId = parseInt(req.params.clientId || req.query.clientId);
  
  // Admin pode ver todos os clientes
  if (req.user.role === 'ADMIN') {
    return next();
  }
  
  // Usuário normal só vê seu próprio cliente
  if (userClientId !== requestedClientId && requestedClientId !== undefined) {
    return res.status(403).json({ error: 'Acesso negado' });
  }
  
  // Forçar o clientId do usuário nas queries
  req.clientId = userClientId;
  next();
};

router.get('/dashboard', authMiddleware, clientOnlyMiddleware, async (req, res) => {
  const { clientId } = req;
  
  // Buscar dados APENAS deste cliente
  const devices = await prisma.device.findMany({
    where: { clientId }
  });
  
  const measurements = await prisma.measurement.findMany({
    where: { 
      clientId,
      timestamp: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) }
    }
  });
  
  // ... resto da lógica
});

export default router;
```

---

## 💰 Modelo de Negócio: SaaS Multi-Tenant

### **Planos de Assinatura**

| Plano | Preço/Mês | Dispositivos | Features |
|-------|-----------|--------------|----------|
| **Basic** | R$ 297 | Até 5 | Dashboard básico, alarmes, relatórios mensais |
| **Professional** | R$ 597 | Até 20 | + Análises avançadas, consultoria 2h/mês, API |
| **Enterprise** | R$ 1.497 | Ilimitado | + Consultoria ilimitada, SLA, white-label |
| **Custom** | Sob consulta | Sob medida | Personalização completa |

### **Serviços Adicionais**
- **Consultoria Avançada**: R$ 200/hora
- **Instalação on-site**: R$ 500 + deslocamento
- **Integração customizada**: A partir de R$ 2.000
- **Treinamento**: R$ 150/hora

### **Cálculo de ROI para Cliente**
```
Cliente médio:
- Consumo atual: 5.000 kWh/mês
- Custo: R$ 3.250/mês (R$ 0,65/kWh)
- Economia com otimização: 15-20% = R$ 487-650/mês
- Custo do sistema: R$ 597/mês (plano Pro)
- ROI líquido: R$ -110 a +53/mês (break-even em 1-6 meses)
- Valor da consultoria: Mitigação de multas, otimização contratual
```

---

## 🚀 Plano de Implementação

### **Sprint 1: Infraestrutura Base (Semana 1-2)**
**Objetivo**: Preparar Fidelco e ambientes

**Tarefas**:
- [ ] Configurar Debian 11 no Fidelco
- [ ] Instalar PostgreSQL 16 com acesso remoto seguro
- [ ] Configurar Redis para cache
- [ ] Setup Docker no Fidelco
- [ ] Criar VPN ou túnel SSH seguro (WireGuard/Tailscale)
- [ ] Configurar backup automático para Google Cloud Storage
- [ ] Configurar SSL com Let's Encrypt
- [ ] Setup Traefik como reverse proxy

**Deliverables**:
- ✅ Fidelco operacional com PostgreSQL
- ✅ Backup automático configurado
- ✅ Acesso remoto seguro

---

### **Sprint 2: Schema e Migração (Semana 3-4)**
**Objetivo**: Criar banco unificado e migrar dados

**Tarefas**:
- [ ] Criar schema multi-tenant (SQL acima)
- [ ] Adicionar índices de performance
- [ ] Implementar particionamento de séries temporais
- [ ] Migrar dados do SQLite para PostgreSQL (se existirem)
- [ ] Criar seeds de dados de teste
- [ ] Configurar Prisma para conectar no Fidelco
- [ ] Implementar Row-Level Security (RLS) no PostgreSQL

**Deliverables**:
- ✅ Schema multi-tenant funcional
- ✅ Dados de teste criados
- ✅ Conexão Prisma→Fidelco funcionando

---

### **Sprint 3: Backend Multi-Tenant (Semana 5-6)**
**Objetivo**: Adaptar APIs para multi-tenancy

**Tarefas**:
- [ ] Implementar middleware de tenant (FastAPI e Node.js)
- [ ] Adicionar filtros de client_id em todos os CRUDs
- [ ] Implementar service de integração entre os sistemas
- [ ] Criar endpoint de análise de economia
- [ ] Implementar sistema de notificações (email/WhatsApp)
- [ ] Adicionar logs de auditoria por cliente
- [ ] Implementar rate limiting por cliente

**Deliverables**:
- ✅ APIs isoladas por cliente
- ✅ Integração FastAPI↔Node.js funcionando
- ✅ Sistema de análise de economia

---

### **Sprint 4: Frontend Cliente (Semana 7-8)**
**Objetivo**: Criar portal isolado por cliente

**Tarefas**:
- [ ] Criar layout white-label customizável
- [ ] Implementar dashboard do cliente
- [ ] Tela de dispositivos e status
- [ ] Gráficos de consumo em tempo real
- [ ] Página de alarmes e histórico
- [ ] Relatórios mensais em PDF
- [ ] Área de consultoria (chat/tickets)
- [ ] Documentação/FAQ para clientes

**Deliverables**:
- ✅ Portal cliente funcional
- ✅ Dashboard responsivo
- ✅ Relatórios automáticos

---

### **Sprint 5: Admin Dashboard (Semana 9-10)**
**Objetivo**: Painel de gestão de todos os clientes

**Tarefas**:
- [ ] Dashboard de visão geral (todos os clientes)
- [ ] Gestão de clientes (CRUD + assinaturas)
- [ ] Gestão de dispositivos global
- [ ] Monitoramento de alarmes agregados
- [ ] Sistema de cobrança/faturamento
- [ ] Relatórios de consultoria
- [ ] Analytics de uso do sistema
- [ ] Health check de dispositivos

**Deliverables**:
- ✅ Admin dashboard completo
- ✅ Gestão de assinaturas
- ✅ Faturamento automatizado

---

### **Sprint 6: Testes e Deploy (Semana 11-12)**
**Objetivo**: Validar e colocar em produção

**Tarefas**:
- [ ] Testes de carga (múltiplos clientes simultâneos)
- [ ] Testes de isolamento (segurança multi-tenant)
- [ ] Testes de failover (queda do Fidelco)
- [ ] Deploy frontend no Vercel
- [ ] Deploy backend no Fidelco (Docker)
- [ ] Configurar monitoramento (Grafana + Prometheus)
- [ ] Documentação completa
- [ ] Treinamento interno

**Deliverables**:
- ✅ Sistema em produção
- ✅ Monitoramento ativo
- ✅ Documentação completa

---

## 🔒 Segurança Multi-Tenant

### **Princípios de Isolamento**

#### **1. Isolamento de Dados**
```sql
-- Row-Level Security (RLS) no PostgreSQL
ALTER TABLE measurements ENABLE ROW LEVEL SECURITY;

CREATE POLICY client_isolation_policy ON measurements
    USING (client_id = current_setting('app.current_client_id')::integer);

-- No código, setar o client_id no contexto
SET app.current_client_id = 123;
```

#### **2. Autenticação e Autorização**
```typescript
// JWT com client_id embutido
const token = jwt.sign({
  userId: user.id,
  clientId: user.clientId,
  role: user.role,
  email: user.email
}, JWT_SECRET);

// Middleware verifica client_id em todas as requests
```

#### **3. Rate Limiting por Cliente**
```typescript
// Limites diferentes por plano
const rateLimits = {
  basic: { requests: 100, window: '1m' },
  professional: { requests: 500, window: '1m' },
  enterprise: { requests: 10000, window: '1m' }
};
```

---

## 📊 Métricas de Sucesso

### **KPIs Técnicos**
- **Uptime**: > 99.5% (objetivo: 99.9%)
- **Latência API**: < 200ms (P95)
- **Taxa de erro**: < 0.1%
- **Tempo de resposta dashboard**: < 2s

### **KPIs de Negócio**
- **MRR** (Monthly Recurring Revenue): Meta inicial R$ 10k/mês
- **CAC** (Customer Acquisition Cost): < R$ 500/cliente
- **LTV** (Lifetime Value): > R$ 10.000/cliente
- **Churn**: < 5% ao mês
- **NPS**: > 70

### **KPIs de Consultoria**
- **Economia média gerada**: > 15% do consumo
- **ROI médio do cliente**: Positivo em < 6 meses
- **Satisfação com consultoria**: > 4.5/5

---

## 🛠️ Stack Tecnológica Final

### **Infraestrutura**
```yaml
Production:
  Database: PostgreSQL 16 (Fidelco Debian 11)
  Cache: Redis (Fidelco)
  Backup: Google Cloud Storage
  Monitoring: Grafana + Prometheus
  Reverse Proxy: Traefik
  VPN: WireGuard/Tailscale

Cloud Services:
  Frontend: Vercel (React)
  Auth Backup: Supabase Auth
  Storage: Google Cloud Storage
  Functions: Firebase Functions (alarmes, notificações)
  Email: Google Workspace
  Analytics: Google Analytics + BigQuery

Development:
  Version Control: Git + GitHub
  CI/CD: GitHub Actions
  Documentation: Markdown + Docusaurus
```

### **Backend**
```yaml
Service 1 (Energy Monitoring):
  Language: Python 3.11
  Framework: FastAPI
  ORM: SQLAlchemy
  Features: Modbus, Analytics, Alarmes

Service 2 (Asset Management):
  Language: Node.js + TypeScript
  Framework: Express
  ORM: Prisma
  Features: IA/RAG, Financeiro, Gestão
```

### **Frontend**
```yaml
Client Portal:
  Framework: React 18 + TypeScript
  Build: Vite
  Styling: Tailwind CSS
  State: Zustand
  Charts: Chart.js
  Deploy: Vercel

Admin Dashboard:
  Same stack + Admin features
```

---

## 💡 Recomendações Estratégicas

### **Curto Prazo (3 meses)**
1. **Foco no MVP multi-tenant**: Priorizar funcionalidades core
2. **Onboarding de 3-5 clientes beta**: Validar modelo de negócio
3. **Refinar algoritmo de economia**: Dados reais > estimativas
4. **Documentar casos de sucesso**: Marketing e vendas

### **Médio Prazo (6-12 meses)**
1. **Expandir base de clientes**: Meta 30-50 clientes
2. **Automatizar consultoria**: IA para análises automáticas
3. **Integração com ERPs**: SAP, TOTVS, etc
4. **Mobile app**: Para técnicos de campo

### **Longo Prazo (12+ meses)**
1. **Marketplace de serviços**: Instaladores, integradores
2. **Certificação técnica**: Tornar-se referência
3. **Expansão geográfica**: Outras regiões/países
4. **Aquisições estratégicas**: Tecnologias complementares

---

## 📚 Documentação Complementar

### **Arquivos Relacionados**
- `README.md` - Visão geral de cada projeto
- `DEPLOY_VERCEL.md` - Deploy do Energy Meter
- `SISTEMA_AVANCADO.md` - Sistema PostgreSQL avançado
- `REMOTE_ACCESS.md` - Configuração de acesso remoto
- `SEGURANCA_VARIAVEIS.md` - Gestão de secrets

### **Documentação a Criar**
- [ ] `MANUAL_CLIENTE.md` - Guia do usuário final
- [ ] `API_DOCUMENTATION.md` - Referência completa de APIs
- [ ] `ADMIN_GUIDE.md` - Manual do administrador
- [ ] `TROUBLESHOOTING.md` - Resolução de problemas
- [ ] `BUSINESS_PLAN.md` - Plano de negócio detalhado

---

## 🎯 Próximos Passos Imediatos

### **Ações Prioritárias (Esta Semana)**

1. **Preparar Fidelco**
   ```bash
   # No servidor Fidelco
   sudo apt update && sudo apt install -y postgresql-16 redis-server docker.io
   ```

2. **Criar Schema Multi-Tenant**
   - Executar SQL fornecido acima
   - Testar conexão remota

3. **Adaptar Energy Meter**
   - Adicionar middleware de tenant
   - Implementar filtros por client_id

4. **Testar Integração Básica**
   - Energy Meter → PostgreSQL no Fidelco
   - Node.js → PostgreSQL no Fidelco

5. **Criar Cliente de Teste**
   - Cadastrar empresa fictícia
   - Adicionar dispositivos
   - Simular medições

---

## ✅ Checklist de Validação

### **Técnico**
- [ ] Fidelco operacional com PostgreSQL
- [ ] Backup automático funcionando
- [ ] APIs com isolamento multi-tenant
- [ ] Portal cliente funcional
- [ ] Admin dashboard completo
- [ ] Monitoramento ativo
- [ ] Testes de carga aprovados

### **Negócio**
- [ ] 3 clientes beta ativos
- [ ] Faturamento recorrente implementado
- [ ] Casos de sucesso documentados
- [ ] Preços validados pelo mercado
- [ ] Modelo de consultoria definido
- [ ] Material de vendas pronto

### **Conformidade**
- [ ] LGPD compliance
- [ ] Termos de uso e privacidade
- [ ] Contratos de nível de serviço (SLA)
- [ ] Seguro de responsabilidade civil
- [ ] Nota fiscal eletrônica

---

## 🚀 Visão de Futuro

**Objetivo Final**: Tornar-se a plataforma líder em gestão energética inteligente no Brasil

**Diferencial Competitivo**:
- ✅ Infraestrutura própria (independência)
- ✅ Análises proprietárias avançadas
- ✅ Consultoria especializada incluída
- ✅ Multi-tenant escalável
- ✅ IA/ML para predições
- ✅ Integração completa IoT

**Meta 2026**:
- 💰 R$ 100k MRR
- 👥 150+ clientes ativos
- 🌐 Cobertura nacional
- 🏆 Referência no setor

---

**Documento criado em**: 18/10/2025  
**Última atualização**: 18/10/2025  
**Versão**: 1.0  
**Autor**: Análise técnica consolidada para convergência dos sistemas PIENG

---

## 📞 Contato e Suporte

**Desenvolvedor**: Flavio  
**Infraestrutura**: Fidelco (Debian 11) + Google Cloud  
**Status**: ✅ Pronto para implementação

