# 🔒 Segurança de Credenciais - PIENG

> ⚠️ **ATENÇÃO**: Este documento é CRÍTICO para a segurança do projeto!

---

## ✅ Checklist de Segurança

### **Arquivos Protegidos (NUNCA commitar)**

- [x] `.env` - Protegido no `.gitignore` linha 25
- [x] `credentials/` - Protegido no `.gitignore` linha 80
- [x] `secrets/` - Protegido no `.gitignore` linha 81
- [x] `test_results_*.json` - Protegido (podem conter device IDs)
- [x] `tuya_devices_*.json` - Protegido (contém device IDs e local keys)
- [x] `*.key`, `*.pem`, `*.p12` - Certificados protegidos

---

## 📝 Credenciais no .env

### **O que está no .env**:

```env
# Tuya IoT (NUNCA exponha!)
TUYA_ACCESS_ID=seu_access_id_real
TUYA_ACCESS_SECRET=seu_access_secret_real
TUYA_API_REGION=us

# PostgreSQL (produção)
DATABASE_URL=postgresql://pieng_admin:senha_real@IP_FIDELCO:5432/pieng_production

# APIs pagas
OPENAI_API_KEY=sk-proj-...
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-key.json

# Segurança
JWT_SECRET=chave_super_secreta_aqui
JWT_REFRESH_SECRET=outra_chave_secreta
```

### **O que NÃO fazer**:

❌ Nunca copiar `.env` para outros arquivos  
❌ Nunca printar credenciais no console  
❌ Nunca logar credenciais (mesmo em desenvolvimento)  
❌ Nunca enviar `.env` por email/Slack/WhatsApp  
❌ Nunca commitar `.env` no Git  
❌ Nunca usar credenciais de produção em desenvolvimento  

### **O que fazer**:

✅ Usar `.env` apenas localmente  
✅ Compartilhar apenas `env.example` (sem valores reais)  
✅ Criar `.env` separado para cada ambiente (dev, staging, prod)  
✅ Rotacionar credenciais periodicamente  
✅ Usar variáveis de ambiente do sistema em produção  

---

## 🔐 Hierarquia de Segurança

### **1. Desenvolvimento Local**
```
.env (local, não commitado)
↓
Aplicação lê com python-dotenv
↓
Nunca expõe em logs/prints
```

### **2. Servidor Fidelco (Produção)**
```
Variáveis de ambiente do sistema
↓
export TUYA_ACCESS_ID="..." (no .bashrc ou systemd)
↓
Aplicação lê via os.getenv()
↓
Nunca salva em disco
```

### **3. Serviços Cloud (Vercel/Netlify)**
```
Painel de variáveis de ambiente
↓
Configurar no dashboard do serviço
↓
Nunca em código-fonte
```

---

## 🚨 Em Caso de Vazamento

Se você acidentalmente expôs credenciais:

### **1. IMEDIATO (5 minutos)**
- [ ] Revogar/regenerar credenciais na plataforma origem
- [ ] Tuya: https://iot.tuya.com/ → Projeto → Regenerar Secret
- [ ] OpenAI: https://platform.openai.com/api-keys → Revogar
- [ ] Trocar senhas do PostgreSQL

### **2. Git History (se commitou)**
```bash
# Se commitou mas não deu push
git reset --soft HEAD~1
git restore --staged .env

# Se já deu push (CRÍTICO!)
# 1. Regenerar TODAS as credenciais
# 2. Limpar histórico do Git (BFG Repo-Cleaner)
# 3. Force push (se tiver permissão)
# 4. Notificar time
```

### **3. Rotação de Credenciais**
- [ ] Gerar novas credenciais
- [ ] Atualizar `.env` localmente
- [ ] Atualizar variáveis em produção
- [ ] Testar aplicação
- [ ] Documentar incidente

---

## 📋 Checklist de Deploy

Antes de fazer deploy:

### **Desenvolvimento → Produção**

- [ ] `.env` está no `.gitignore`
- [ ] Não há prints de credenciais no código
- [ ] Variáveis carregadas via `os.getenv()` ou `settings`
- [ ] Credenciais diferentes para dev e prod
- [ ] Logs não contêm dados sensíveis
- [ ] Testes não expõem credenciais
- [ ] API keys com rate limiting configurado

### **Revisão de Código**

```bash
# Procurar por possíveis credenciais expostas
git grep -i "access.*id\|secret\|password\|key\|token" -- "*.py" "*.js" "*.ts"

# Verificar se .env está protegido
git check-ignore .env
# Deve retornar: .env

# Ver últimos commits
git log --oneline -10
# Verificar se não há commits com mensagens suspeitas
```

---

## 🛡️ Boas Práticas

### **Desenvolvimento**

```python
# ✅ CORRETO
import os
from dotenv import load_dotenv

load_dotenv()
TUYA_KEY = os.getenv("TUYA_ACCESS_ID")

if not TUYA_KEY:
    raise ValueError("TUYA_ACCESS_ID não configurada")

# ❌ ERRADO
TUYA_KEY = "aabbccddee1234567890"  # NUNCA fazer isso!
```

### **Logging Seguro**

```python
# ✅ CORRETO
logger.info(f"Conectando ao Tuya (região: {region})")

# ❌ ERRADO
logger.info(f"Tuya credentials: {access_id}:{access_secret}")  # NUNCA!
```

### **Tratamento de Erros**

```python
# ✅ CORRETO
try:
    cloud = tinytuya.Cloud(apiKey=key, apiSecret=secret)
except Exception as e:
    logger.error("Erro ao conectar Tuya")
    # Não logar 'e' se contiver credenciais!

# ❌ ERRADO
except Exception as e:
    logger.error(f"Erro: {e}")  # Pode expor credenciais na mensagem!
```

---

## 📚 Referências

### **Padrões de Segurança**

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **12 Factor App**: https://12factor.net/config
- **NIST Guidelines**: https://csrc.nist.gov/publications/sp800

### **Ferramentas de Verificação**

```bash
# GitLeaks - detectar secrets em commits
docker run --rm -v $(pwd):/repo zricethezav/gitleaks:latest detect --source /repo

# TruffleHog - escanear histórico Git
trufflehog git file://. --only-verified

# git-secrets - prevenir commits com secrets
git secrets --scan
```

---

## 🎓 Treinamento da Equipe

### **Onboarding de Novos Desenvolvedores**

1. ✅ Ler este documento completo
2. ✅ Receber `env.example` (não o `.env` real)
3. ✅ Criar próprio `.env` com credenciais de desenvolvimento
4. ✅ Confirmar que `.env` está no `.gitignore`
5. ✅ Fazer teste de commit (verificar que `.env` não entra)

### **Revisão Trimestral**

- [ ] Rotacionar todas as credenciais
- [ ] Auditar logs por exposições
- [ ] Verificar permissões de acesso
- [ ] Atualizar este documento

---

## ⚠️ Compliance e Regulamentação

### **LGPD (Lei Geral de Proteção de Dados)**

- Credenciais são dados sensíveis
- Acesso restrito apenas a pessoal autorizado
- Logs de auditoria de quem acessa
- Direito ao esquecimento (revogar credenciais de ex-colaboradores)

### **PCI DSS** (se aceitar cartões)

- Credenciais nunca em texto plano no banco
- Criptografia em trânsito (TLS)
- Criptografia em repouso (encrypt at rest)

---

## ✅ Status Atual

**Última verificação**: 18/10/2025

- [x] `.env` protegido no `.gitignore`
- [x] `env.example` criado sem credenciais
- [x] Scripts não solicitam credenciais via input
- [x] Credenciais carregadas via `dotenv`
- [x] Logs não expõem dados sensíveis
- [x] Documentação de segurança criada

**Responsável**: Flávio  
**Próxima revisão**: 18/01/2026

---

**⚠️ LEMBRE-SE: Segurança não é um recurso, é um requisito!**

Se tiver dúvidas sobre segurança, SEMPRE pergunte antes de commitar!

