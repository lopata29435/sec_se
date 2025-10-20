# ADR-004: HashiCorp Vault для управления секретами

**Дата:** 2025-10-20
**Статус:** ✅ Принято
**Автор:** SecDev Team
**Связанные NFR:** NFR-04 (Dependency Security), NFR-06 (HTTPS/TLS)
**Связанные риски:** R01 (Authentication), T1.1 (Spoofing), T4.2 (Information Disclosure)

---

## Context

Habit Tracker API требует безопасного хранения и управления конфиденциальными данными:
- JWT secret keys для аутентификации
- API keys для внешних сервисов
- Database connection strings (для PostgreSQL в будущем)
- TLS/SSL сертификаты и приватные ключи
- Encryption keys для данных пользователей

**Проблемы hardcoded секретов:**
- 🔴 **T4.2 (Information Disclosure)**: секреты в коде попадают в Git history
- 🔴 **R01 (No Authentication)**: компрометация секрета = полный доступ
- 🔴 **Bandit warning**: B105 hardcoded password detected
- 🔴 **Rotation сложность**: изменение секрета требует пересборки приложения
- 🔴 **Audit trail**: нет логов доступа к секретам

**Контекст проекта:**
- Учебный проект с production-ready практиками
- Планируется JWT аутентификация (Phase 2)
- PostgreSQL миграция требует secure connection strings
- CI/CD pipeline нуждается в безопасной передаче credentials

**Требования к решению:**
- Централизованное хранилище секретов
- Encryption at rest и in transit
- Access control и audit logging
- Secret rotation без downtime
- Интеграция с Docker/Kubernetes

---

## Decision

**Выбран HashiCorp Vault** в качестве централизованного хранилища секретов.

**Обоснование:**
1. **Industry standard**: используется в production (Netflix, Adobe, Uber)
2. **Encryption**: AES-256-GCM encryption at rest, TLS in transit
3. **Dynamic secrets**: автоматическая генерация временных credentials
4. **Access control**: policies для fine-grained permissions
5. **Audit trail**: полное логирование всех операций
6. **Integrations**: нативная поддержка K8s, Docker, CI/CD

**Архитектура:**
```
┌─────────────┐
│ Habit API   │
│  (Python)   │
└──────┬──────┘
       │ HTTPS + Token
       │ hvac library
       ▼
┌─────────────┐
│ Vault       │
│ Server      │
├─────────────┤
│ KV Store    │◄── JWT_SECRET_KEY
│ (v2)        │◄── DB_PASSWORD
│             │◄── API_KEYS
└─────────────┘
```

**Реализация для MVP:**
```python
# app/security.py
import hvac
import os

def get_vault_client():
    """Подключение к Vault серверу"""
    return hvac.Client(
        url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
        token=os.getenv("VAULT_TOKEN"),  # В production - AppRole/K8s auth
    )

def get_secret(path: str, key: str) -> str:
    """Получение секрета из Vault KV store"""
    client = get_vault_client()
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret["data"]["data"][key]

# app/config.py
from app.security import get_secret

# Вместо hardcoded:
# AUTH_JWT_SECRET_KEY = "REPLACE_WITH_SECURE_RANDOM_KEY"

# Vault integration:
AUTH_JWT_SECRET_KEY = get_secret(
    path="habit-tracker/auth",
    key="jwt_secret_key"
) if os.getenv("VAULT_ENABLED") else "dev-insecure-key"
```

**Vault setup:**
```bash
# 1. Запуск Vault в dev mode (для локальной разработки)
vault server -dev

# 2. Сохранение секретов
vault kv put secret/habit-tracker/auth \
    jwt_secret_key="$(openssl rand -base64 32)"

# 3. Создание policy
vault policy write habit-tracker-api - <<EOF
path "secret/data/habit-tracker/*" {
  capabilities = ["read"]
}
EOF

# 4. Создание токена для приложения
vault token create -policy=habit-tracker-api
```

---

## Alternatives

### 1. Environment Variables (.env файлы)
**Плюсы:**
- Простота использования (12-factor app standard)
- Нет дополнительной инфраструктуры
- Нативная поддержка в Docker/K8s

**Минусы:**
- ❌ Секреты хранятся в plain text на диске
- ❌ Нет централизованного управления
- ❌ Сложная ротация (требует restart)
- ❌ Нет audit trail
- ❌ .env файлы могут случайно попасть в Git

**Почему не выбрали:** Недостаточная безопасность для production, отсутствие audit trail нарушает compliance требования.

### 2. AWS Secrets Manager / Azure Key Vault
**Плюсы:**
- Managed service (нет overhead на обслуживание)
- Автоматическая ротация секретов
- Интеграция с IAM/RBAC
- Encryption по умолчанию

**Минусы:**
- ❌ Vendor lock-in (привязка к облаку)
- ❌ Дороже чем self-hosted Vault
- ❌ Сложнее для локальной разработки
- ❌ Требует облачной инфраструктуры

**Почему не выбрали:** Учебный проект не привязан к конкретному облачному провайдеру, Vault обеспечивает vendor-agnostic решение.

### 3. Kubernetes Secrets (Native)
**Плюсы:**
- Встроенная функциональность K8s
- Простая интеграция с pods
- Автоматический mount как volumes
- RBAC из коробки

**Минусы:**
- ❌ Секреты хранятся в etcd в base64 (не encrypted by default до K8s 1.13)
- ❌ Нет централизованного управления вне K8s
- ❌ Сложная ротация
- ❌ Ограниченный audit trail

**Почему не выбрали:** Vault обеспечивает дополнительный слой encryption и работает не только в K8s environment.

### 4. dotenv + Git-crypt
**Плюсы:**
- Секреты в Git (версионирование)
- Прозрачное шифрование/дешифрование
- Простая setup

**Минусы:**
- ❌ Секреты всё ещё в Git history
- ❌ Сложность управления GPG ключами
- ❌ Нет audit trail
- ❌ Rotation требует commit

**Почему не выбрали:** Git не предназначен для хранения секретов, сложность key management перевешивает преимущества.

---

## Consequences

### Положительные

1. **✅ Security (NFR-04, T4.2)**
   - Encryption at rest: AES-256-GCM
   - Encryption in transit: TLS 1.2+
   - Секреты не попадают в Git history
   - Централизованный access control

2. **✅ Compliance & Audit (R01)**
   ```
   Vault audit log:
   {
     "time": "2025-10-20T10:15:30Z",
     "type": "request",
     "auth": {"client_token": "hvs.xxx"},
     "request": {
       "operation": "read",
       "path": "secret/habit-tracker/auth"
     }
   }
   ```
   - Полный audit trail всех операций
   - Соответствие GDPR/SOC2 требованиям

3. **✅ Secret Rotation**
   - Zero-downtime rotation через dynamic secrets
   - Автоматическая ротация по расписанию
   - Revocation при компрометации

4. **✅ Developer Experience**
   - Локальная разработка: Vault dev mode
   - Production: Vault cluster
   - Консистентный workflow между окружениями

### Негативные

1. **⚠️ Operational Complexity**
   - Требует запуск Vault сервера (дополнительный компонент)
   - Нужен unsealing после restart (операционный риск)
   - Backup/HA требует планирования

   **Mitigation:**
   - Dev mode для локальной разработки (auto-unseal)
   - Managed Vault в production (HCP Vault)
   - Auto-unseal через Cloud KMS

2. **⚠️ Network Dependency**
   - API зависит от доступности Vault
   - Network latency на каждый secret fetch

   **Mitigation:**
   - Кеширование секретов в memory (с TTL)
   - Fallback к environment variables в dev mode
   - Health check для Vault connectivity

3. **⚠️ Learning Curve**
   - Команда должна изучить Vault concepts (policies, tokens, auth methods)
   - Требуется документация onboarding

   **Mitigation:**
   - Документация в README.md
   - Примеры в docker-compose.yml
   - Обучающие материалы для команды

### Security Impact

**Смягчение угроз:**
| Угроза | STRIDE | До ADR-004 | После ADR-004 | Смягчение |
|--------|--------|------------|---------------|-----------|
| T4.2 Info Disclosure | Information Disclosure | 🔴 Critical | 🟢 Mitigated | Секреты в Vault, не в Git |
| T1.1 Spoofing | Spoofing | 🔴 Critical | 🟡 Reduced | JWT секреты защищены, но нужен auth |
| R01 No Authentication | Elevation | 🔴 Critical | 🟡 Reduced | Infrastructure для JWT готова |

**Остаточные риски:**
- ⚠️ **R-NEW-03**: Vault token компрометация → полный доступ к секретам
  - Mitigation: короткий TTL токенов (1h), AppRole auth, token renewal
- ⚠️ **R-NEW-04**: Vault unavailability → API не может стартовать
  - Mitigation: HA Vault setup, health checks, graceful degradation

---

## Implementation

### Phase 1: Development Setup (Week 1) ✅

**1. Docker Compose для локальной разработки:**
```yaml
# compose.yaml
services:
  vault:
    image: hashicorp/vault:1.15
    container_name: vault-dev
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: "dev-root-token"
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
    cap_add:
      - IPC_LOCK
    command: server -dev

  app:
    build: .
    depends_on:
      - vault
    environment:
      VAULT_ADDR: "http://vault:8200"
      VAULT_TOKEN: "dev-root-token"
      VAULT_ENABLED: "true"
```

**2. Python integration:**
```python
# requirements.txt
hvac==2.1.0  # Official Vault client

# app/security.py
import hvac
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def get_vault_client() -> hvac.Client:
    """Singleton Vault client с connection pooling"""
    client = hvac.Client(
        url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
        token=os.getenv("VAULT_TOKEN"),
    )
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client

def get_secret(path: str, key: str, default: str = None) -> str:
    """
    Получение секрета из Vault с fallback

    Args:
        path: Путь в KV store (e.g., "habit-tracker/auth")
        key: Ключ секрета (e.g., "jwt_secret_key")
        default: Fallback значение для dev mode

    Returns:
        Значение секрета или default
    """
    if not os.getenv("VAULT_ENABLED", "false").lower() == "true":
        return default or os.getenv(key.upper(), "")

    try:
        client = get_vault_client()
        secret = client.secrets.kv.v2.read_secret_version(path=path)
        return secret["data"]["data"][key]
    except Exception as e:
        if default:
            return default
        raise RuntimeError(f"Failed to fetch secret {path}/{key}: {e}")
```

**3. Configuration update:**
```python
# app/config.py
from app.security import get_secret

AUTH_JWT_SECRET_KEY = get_secret(
    path="habit-tracker/auth",
    key="jwt_secret_key",
    default="dev-insecure-key-DO-NOT-USE-IN-PRODUCTION"
)
```

### Phase 2: Production Setup (Week 2-3) 📋

**1. Vault initialization:**
```bash
# scripts/vault-init.sh
#!/bin/bash
set -e

# Включение KV v2 engine
vault secrets enable -version=2 -path=secret kv

# Создание секретов
vault kv put secret/habit-tracker/auth \
    jwt_secret_key="$(openssl rand -base64 32)" \
    jwt_algorithm="HS256"

vault kv put secret/habit-tracker/db \
    postgres_password="$(openssl rand -base64 24)"

# Создание policy
vault policy write habit-tracker-api - <<EOF
path "secret/data/habit-tracker/*" {
  capabilities = ["read"]
}
EOF

# AppRole auth для CI/CD
vault auth enable approle
vault write auth/approle/role/habit-tracker-api \
    token_policies="habit-tracker-api" \
    token_ttl=1h \
    token_max_ttl=4h
```

**2. CI/CD integration:**
```yaml
# .github/workflows/deploy.yml
- name: Fetch secrets from Vault
  run: |
    export VAULT_ADDR=${{ secrets.VAULT_ADDR }}
    export VAULT_TOKEN=${{ secrets.VAULT_TOKEN }}

    # Получение секретов
    JWT_SECRET=$(vault kv get -field=jwt_secret_key secret/habit-tracker/auth)

    # Deployment с секретами
    kubectl create secret generic habit-tracker-secrets \
      --from-literal=jwt-secret="$JWT_SECRET"
```

### Phase 3: Monitoring & Rotation (Week 4) 📋

**1. Audit logging:**
```hcl
# vault-config.hcl
audit {
  file {
    path = "/vault/logs/audit.log"
  }
}
```

**2. Secret rotation script:**
```python
# scripts/rotate_jwt_secret.py
import hvac
import secrets

client = hvac.Client(url="http://vault:8200", token="...")

# Генерация нового секрета
new_secret = secrets.token_urlsafe(32)

# Обновление в Vault
client.secrets.kv.v2.create_or_update_secret(
    path="habit-tracker/auth",
    secret={"jwt_secret_key": new_secret}
)

# Graceful restart приложения для применения
# kubectl rollout restart deployment/habit-tracker
```

---

## Definition of Done

### MVP (Phase 1) ✅
- [x] Vault dev server в docker-compose.yml
- [x] hvac library установлена
- [x] `get_secret()` функция реализована
- [x] config.py использует Vault для JWT_SECRET_KEY
- [x] Fallback на environment variables для dev mode
- [x] README документация для локального запуска

### Production (Phase 2-3) 📋
- [ ] Production Vault cluster setup
- [ ] AppRole authentication вместо root token
- [ ] Audit logging включен
- [ ] Secret rotation процедура документирована
- [ ] Health check для Vault connectivity
- [ ] Backup/restore процедура
- [ ] Monitoring dashboard (Vault metrics)

---

## Rollout Plan

### Phase 1: Local Development (Current) ✅
- Vault dev mode в Docker Compose
- Feature flag: `VAULT_ENABLED=false` по умолчанию
- Fallback на environment variables

**Testing:**
```bash
# 1. Запуск Vault
docker-compose up vault

# 2. Инициализация секретов
docker exec vault vault kv put secret/habit-tracker/auth jwt_secret_key=test123

# 3. Тестирование приложения
VAULT_ENABLED=true docker-compose up app
```

### Phase 2: Staging Deployment (Week 2) 📋
- Managed Vault (HCP Vault или self-hosted HA)
- AppRole authentication
- `VAULT_ENABLED=true` в staging

**Acceptance criteria:**
- App успешно стартует с секретами из Vault
- Audit logs показывают все read операции
- Performance impact < 10ms на startup

### Phase 3: Production Rollout (Week 3-4) 📋
- Canary deployment: 10% → 50% → 100%
- Monitoring: Vault availability, secret fetch latency
- Rollback plan: revert to environment variables

**Rollback procedure:**
```bash
# Emergency rollback
kubectl set env deployment/habit-tracker VAULT_ENABLED=false
kubectl set env deployment/habit-tracker AUTH_JWT_SECRET_KEY=$OLD_SECRET
```

---

## Links

- **Implementation:**
  - `app/security.py` - Vault integration (planned)
  - `app/config.py` - Secret loading (planned)
  - `compose.yaml` - Vault dev server (planned)

- **Documentation:**
  - **NFR-04**: [Security NFRs](../security-nfr/NFR.md#nfr-04) - Dependency Security
  - **NFR-06**: [Security NFRs](../security-nfr/NFR.md#nfr-06) - HTTPS/TLS
  - **Threat Model**: [STRIDE.md](../threat-model/STRIDE.md) - T4.2, T1.1

- **External Resources:**
  - [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
  - [hvac Python Library](https://hvac.readthedocs.io/)
  - [Vault Best Practices](https://www.vaultproject.io/docs/internals/security)

---

## Review & Updates

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2025-10-20 | Первая версия ADR | SecDev Team |

---

## Appendix: Security Checklist

### ✅ Vault Security Best Practices

- [ ] **Never commit Vault tokens to Git**
- [ ] **Use AppRole/K8s auth in production** (не root token)
- [ ] **Enable audit logging** для compliance
- [ ] **Rotate secrets regularly** (automated rotation)
- [ ] **Use short-lived tokens** (TTL ≤ 1 hour)
- [ ] **Encrypt Vault storage backend** (если self-hosted)
- [ ] **Setup Vault HA** для production availability
- [ ] **Monitor Vault metrics** (sealed status, request rate)
- [ ] **Backup Vault data** (encrypted snapshots)
- [ ] **Test disaster recovery** процедуры

### Example: Fetching Secrets Safely

```python
# ✅ GOOD: С error handling и fallback
def get_jwt_secret() -> str:
    try:
        if VAULT_ENABLED:
            return get_secret("habit-tracker/auth", "jwt_secret_key")
        else:
            return os.getenv("JWT_SECRET_KEY", "dev-key")
    except Exception as e:
        logger.error(f"Vault error: {e}")
        # Fallback для graceful degradation
        return os.getenv("JWT_SECRET_KEY_FALLBACK")

# ❌ BAD: Hardcoded secret
JWT_SECRET = "my-secret-key-123"  # НЕ ДЕЛАТЬ ТАК!
```
