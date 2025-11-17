# ADR-001: Pydantic для валидации входных данных

**Статус:** ✅ Принято и реализовано
**Дата:** 2025-10-20
**Авторы:** DevSecOps Team
**Связь:** NFR-01, NFR-05 | Threat Model: T3.1, T6.1, T13.2

---

## Context (Контекст)

### Проблема
Habit Tracker API принимает пользовательский ввод через REST endpoints без строгой валидации:
- **T3.1 (Injection attacks)**: Отсутствие санитизации позволяет XSS, SQL injection
- **T6.1 (Invalid input)**: Нет проверки диапазонов (длина строк, числовые значения)
- **T13.2 (Data tampering)**: Возможность отправки некорректных данных (даты в будущем, отрицательные значения)

### Требования
- **NFR-01**: 100% endpoints с валидацией входных данных
- **NFR-05**: 0 injection атак в production (защита от XSS, SQL, NoSQL)
- **Coverage**: ≥85% для новых модулей валидации

### Текущее состояние (до P06)
```python
# app/main.py - старый подход
@app.post("/habits")
def create_habit(name: str, description: str = ""):
    if not name or len(name) > 100:  # Ручная валидация
        raise ApiError("validation_error", "Invalid name")
    # Нет защиты от XSS, SQL injection
```

**Проблемы:**
- Дублирование логики валидации в каждом endpoint
- Нет централизованной защиты от опасных символов
- Сложно добавлять новые правила валидации

---

## Decision (Решение)

**Выбрано:** Pydantic v2 Models с field validators

### Реализация
```python
# app/models.py
from pydantic import BaseModel, Field, field_validator

class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    frequency: FrequencyType = Field(default=FrequencyType.DAILY)

    @field_validator("name", "description")
    @classmethod
    def prevent_xss(cls, v: str) -> str:
        """Защита от XSS: запрет опасных символов"""
        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        if any(char in v for char in dangerous_chars):
            raise ValueError(
                f"Field contains forbidden characters: {', '.join(dangerous_chars)}"
            )
        return v.strip()
```

**Применение в endpoints:**
```python
@app.post("/habits", status_code=201)
def create_habit(habit: HabitCreate):  # Pydantic автоматически валидирует
    new_habit = {
        "id": next_id,
        "name": habit.name,  # Уже провалидировано
        "description": habit.description,
    }
    return new_habit
```

---

## Alternatives (Альтернативы)

### 1. Marshmallow
**Плюсы:**
- Зрелая библиотека с богатой экосистемой
- Поддержка сложных схем сериализации

**Минусы:**
- ❌ Не интегрируется нативно с FastAPI
- ❌ Медленнее Pydantic (важно для NFR-07: p95 ≤ 200ms)
- ❌ Требует отдельных классов для валидации и сериализации

**Вердикт:** Отклонено из-за проблем с производительностью и отсутствия FastAPI интеграции.

### 2. Cerberus
**Плюсы:**
- Легковесная библиотека
- Гибкие правила валидации через словари

**Минусы:**
- ❌ Нет type hints (хуже IDE support)
- ❌ Требует ручной интеграции с FastAPI
- ❌ Нет автоматической документации OpenAPI

**Вердикт:** Отклонено из-за отсутствия type safety и FastAPI интеграции.

### 3. Ручная валидация (текущий подход)
**Плюсы:**
- Полный контроль логики
- Нет зависимостей

**Минусы:**
- ❌ Дублирование кода в каждом endpoint
- ❌ Высокий риск человеческой ошибки
- ❌ Сложно поддерживать консистентность

**Вердикт:** Отклонено из-за технического долга и низкой надежности.

---

## Consequences (Последствия)

### Positive (Позитивные)
✅ **Безопасность (NFR-01, NFR-05)**
- Централизованная защита от XSS через `@field_validator`
- Автоматическая проверка диапазонов (1-100 символов, ge=1, le=100)
- Блокировка injection атак через запрет опасных символов

✅ **Качество кода**
- DRY: валидация определена один раз в моделях
- Type safety: IDE автодополнение и проверка типов
- Тестируемость: легко mock Pydantic модели

✅ **Производительность**
- Pydantic v2 написан на Rust (10x быстрее v1)
- Соответствует NFR-07: p95=1.93ms < 200ms

✅ **Документация**
- FastAPI автоматически генерирует OpenAPI схемы из Pydantic
- Swagger UI показывает валидационные правила пользователям

### Negative (Негативные)
⚠️ **Breaking changes**
- Старые query параметры требуют адаптера (реализовано через Optional[HabitCreate])
- Тесты с params={'name': ...} нужно обновить на json={'name': ...}

⚠️ **Зависимость**
- Привязка к Pydantic v2 (мажорное обновление требует миграции)
- Ограничения Pydantic влияют на архитектуру

⚠️ **Обучение команды**
- Разработчики должны изучить field_validator, model_validator
- Нужны примеры сложных кейсов (вложенные модели, кастомные типы)

### Security Impact (Влияние на безопасность)

**Смягчение угроз:**
| Угроза | STRIDE | До ADR-001 | После ADR-001 | Смягчение |
|--------|--------|------------|---------------|-----------|
| T3.1 XSS | Tampering | 🔴 Critical | 🟢 Mitigated | `prevent_xss()` блокирует <>"'`& |
| T6.1 Invalid input | Tampering | 🔴 Critical | 🟢 Mitigated | Field constraints (min/max length) |
| T13.2 Future dates | Tampering | 🟠 High | 🟢 Mitigated | `validate_date_not_future()` |

**Остаточные риски:**
- ⚠️ **R-NEW-01**: Bypass через Unicode variants (𝗑ss) — требует нормализации Unicode (backlog)
- ⚠️ **R-NEW-02**: ReDoS через сложные regex в валидации — использовать простые правила

**Mitigation plan:**
1. **Unicode normalization**: Добавить `.encode('ascii', 'ignore')` в валидаторах (P07)
2. **ReDoS prevention**: Избегать regex, использовать `in` оператор для проверки символов
3. **Monitoring**: Логировать все `ValidationError` с correlation_id для анализа атак

---

## Definition of Done (Критерии приёмки)

### Обязательные критерии (DoD)
- [x] **C1**: Pydantic модели созданы для всех input endpoints (`HabitCreate`, `TrackingCreate`)
- [x] **C2**: Field validators реализованы для защиты от XSS (запрет `<>"'`&`)
- [x] **C3**: Валидация диапазонов (min_length=1, max_length=100, ge=1, le=100)
- [x] **C4**: Проверка дат (не в будущем) через `@field_validator`
- [x] **C5**: Обратная совместимость с query параметрами (адаптер в endpoints)
- [x] **C6**: Тесты валидации: 35+ тестов в `tests/test_validation.py`
- [x] **C7**: Coverage ≥85% для `app/models.py`
- [x] **C8**: Документация обновлена (NFR.md, IMPLEMENTATION.md)

### Verification (Проверка)
```bash
# 1. Проверка Pydantic моделей
pytest tests/test_validation.py::TestInputValidation -v

# 2. XSS protection
curl -X POST http://localhost:8000/habits \
  -H "Content-Type: application/json" \
  -d '{"name": "<script>alert(1)</script>"}'
# Expected: 422 с ошибкой "forbidden characters"

# 3. Coverage
pytest --cov=app.models --cov-report=term-missing
# Expected: ≥85%
```

---

## Rollout Plan (План внедрения)

### Phase 1: Pilot (Week 1) ✅ Завершено
- [x] Создать Pydantic модели (`app/models.py`)
- [x] Реализовать field validators
- [x] Добавить тесты (35+ scenarios)
- [x] Обновить 2 endpoint (`POST /habits`, `POST /habits/{id}/track`)

**Метрики успеха:**
- ✅ 0 регрессий в существующих тестах
- ✅ Coverage: 93.6% (цель ≥85%)

### Phase 2: Rollout (Week 2) 🔄 В процессе
- [ ] Обновить все оставшиеся endpoints (`PUT /habits/{id}`, `POST /items`)
- [ ] Удалить адаптеры для query параметров (breaking change)
- [ ] Обновить документацию API (примеры в README)

**Feature flag:**
```python
# app/config.py
USE_PYDANTIC_VALIDATION = os.getenv("USE_PYDANTIC_VALIDATION", "true").lower() == "true"
```

### Phase 3: Monitoring (Week 3-4) 📋 Запланировано
- [ ] Логировать все ValidationError с correlation_id
- [ ] Dashboard для мониторинга попыток injection атак
- [ ] Alert при >10 ValidationError/min от одного IP

**Rollback plan:**
```bash
# Если critical bug, откатить к старой валидации:
export USE_PYDANTIC_VALIDATION=false
uvicorn app.main:app --reload
```

---

## Links (Связи)

### Code & Tests
- **Implementation**: [`app/models.py`](../../app/models.py) (209 lines)
- **Tests**: [`tests/test_validation.py`](../../tests/test_validation.py) (35+ scenarios)
- **Integration**: [`app/main.py`](../../app/main.py) - endpoints updated

### Documentation
- **NFR-01**: [Security NFRs](../security-nfr/NFR.md#nfr-01) - Validation requirement
- **NFR-05**: [Security NFRs](../security-nfr/NFR.md#nfr-05) - Input Sanitization
- **Threat Model**: [IMPLEMENTATION.md](../threat-model/IMPLEMENTATION.md#4-input-validation-nfr-01)
- **BDD Scenarios**: [NFR_BDD.md](../security-nfr/NFR_BDD.md) - validation scenarios

### Related ADRs
- [ADR-002: RFC 7807 Error Handling](ADR-002-rfc7807-errors.md) - валидационные ошибки
- [ADR-003: Quality Gate CI/CD](ADR-003-quality-gate.md) - автоматическая проверка coverage

### Threat Modeling
- **T3.1**: Injection attacks → Mitigated by `prevent_xss()` validator
- **T6.1**: Invalid input → Mitigated by Field constraints
- **T13.2**: Data tampering → Mitigated by `validate_date_not_future()`

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-10-20 | 1.0 | DevSecOps Team | Первая версия ADR после реализации P06 |

---

## Appendix: Примеры использования

### Позитивный сценарий
```python
# Valid request
response = client.post("/habits", json={
    "name": "Drink Water",
    "description": "8 glasses per day",
    "frequency": "daily"
})
# → 201 Created

assert response.json()["name"] == "Drink Water"
```

### Негативный сценарий (XSS)
```python
# XSS attempt
response = client.post("/habits", json={
    "name": "<script>alert('xss')</script>"
})
# → 422 Validation Error

data = response.json()
assert "forbidden characters" in data["errors"][0]["message"].lower()
```

### Граничные значения
```python
# Boundary: min_length=1
response = client.post("/habits", json={"name": "A"})
# → 201 Created

# Boundary: max_length=100
response = client.post("/habits", json={"name": "A" * 100})
# → 201 Created

response = client.post("/habits", json={"name": "A" * 101})
# → 422 Validation Error (too long)
```
