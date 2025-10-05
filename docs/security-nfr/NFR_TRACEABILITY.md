# NFR Traceability Matrix — Habit Tracker API

## Введение

Данный документ устанавливает трассируемость между нефункциональными требованиями (NFR) и конкретными задачами, историями пользователей и релизами проекта.

**Дата:** 2025-10-05
**Версия:** 1.2
**Проект:** Habit Tracker API

---

## 1. NFR → User Stories/Tasks Mapping

### Security NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-01 | Валидация входных данных          | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.09)   |
| NFR-01 | Валидация входных данных          | HABIT-015     | Добавить валидацию всех полей ввода           | High      | Planned     | v1.1 (2025.10)   |
| NFR-02 | Ошибки в формате RFC7807          | HABIT-002     | Стандартизация обработки ошибок               | High      | In Progress | v1.1 (2025.10)   |
| NFR-03 | Rate Limiting                     | HABIT-016     | Добавить rate limiting middleware             | Medium    | Planned     | v1.2 (2025.11)   |
| NFR-04 | Уязвимости зависимостей           | HABIT-003     | Настройка CI/CD с security checks             | High      | Completed   | v1.0 (2025.09)   |
| NFR-04 | Уязвимости зависимостей           | HABIT-017     | Интеграция Dependabot/Safety                  | High      | Planned     | v1.1 (2025.10)   |
| NFR-05 | Input Sanitization                | HABIT-018     | Добавить санитизацию всех входных данных      | High      | Planned     | v1.1 (2025.10)   |
| NFR-06 | HTTPS только                      | HABIT-019     | Настройка TLS для production                  | High      | Planned     | v1.2 (2025.11)   |

### Performance NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-07 | Время ответа GET /habits          | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.10)   |
| NFR-07 | Время ответа GET /habits          | HABIT-025     | Baseline performance tests                    | High      | Completed   | v1.0 (2025.10)   |
| NFR-08 | Время ответа POST /habits         | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.09)   |
| NFR-08 | Время ответа POST /habits         | HABIT-025     | Baseline performance tests                    | High      | Completed   | v1.0 (2025.10)   |
| NFR-09 | Время ответа GET /habits/stats    | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.10)   |
| NFR-09 | Время ответа GET /habits/stats    | HABIT-025     | Baseline performance tests                    | High      | Completed   | v1.0 (2025.10)   |
| NFR-10 | Пропускная способность            | HABIT-020     | Настройка нагрузочного тестирования           | Medium    | Planned     | v1.2 (2025.11)   |
| NFR-11 | Concurrent Users                  | HABIT-020     | Настройка нагрузочного тестирования           | Medium    | Planned     | v1.2 (2025.11)   |

### Reliability NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-12 | API Uptime                        | HABIT-006     | Настройка health check и monitoring           | High      | In Progress | v1.1 (2025.10)   |
| NFR-13 | Error Rate                        | HABIT-002     | Стандартизация обработки ошибок               | High      | In Progress | v1.1 (2025.10)   |
| NFR-14 | Graceful Degradation              | HABIT-021     | Реализация error handling patterns            | High      | Planned     | v1.1 (2025.10)   |
| NFR-15 | Data Consistency                  | HABIT-022     | Добавить data validation слой                 | High      | Planned     | v1.2 (2025.11)   |

### Observability NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-16 | Структурированное логирование     | HABIT-007     | Настройка structured logging                  | Medium    | Planned     | v1.2 (2025.11)   |
| NFR-17 | Health Check эндпоинт             | HABIT-006     | Настройка health check и monitoring           | High      | In Progress | v1.1 (2025.10)   |
| NFR-18 | Метрики производительности        | HABIT-023     | Интеграция Prometheus/OpenTelemetry           | Medium    | Planned     | v1.3 (2025.12)   |

### Code Quality NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-19 | Test Coverage                     | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.09)   |
| NFR-19 | Test Coverage                     | HABIT-008     | Увеличение test coverage до 90%               | High      | Planned     | v1.1 (2025.10)   |
| NFR-20 | Linting                           | HABIT-003     | Настройка CI/CD с security checks             | High      | Completed   | v1.0 (2025.09)   |
| NFR-21 | Static Analysis                   | HABIT-024     | Добавить bandit и safety в CI                 | High      | Planned     | v1.1 (2025.10)   |
| NFR-22 | Dependency Updates                | HABIT-017     | Интеграция Dependabot/Safety                  | Medium    | Planned     | v1.1 (2025.10)   |

### API Design NFRs

| NFR ID | NFR Название                      | Story/Task ID | Story/Task Название                           | Приоритет | Status      | Release/Milestone |
|--------|-----------------------------------|---------------|-----------------------------------------------|-----------|-------------|-------------------|
| NFR-23 | RESTful принципы                  | HABIT-001     | Реализация API эндпоинтов трекера привычек    | Medium    | Completed   | v1.0 (2025.09)   |
| NFR-24 | HTTP коды статуса                 | HABIT-001     | Реализация API эндпоинтов трекера привычек    | High      | Completed   | v1.0 (2025.09)   |
| NFR-25 | API документация                  | HABIT-009     | Генерация OpenAPI спецификации                | Medium    | Planned     | v1.2 (2025.11)   |

---

## 2. User Stories/Tasks → NFR Reverse Mapping

### HABIT-001: Реализация API эндпоинтов трекера привычек ✅

**Статус:** Completed (2025.09)
**Релиз:** v1.0

**Связанные NFR:**
- NFR-01 (Валидация входных данных) — High Priority
- NFR-08 (Время ответа POST /habits) — High Priority
- NFR-19 (Test Coverage) — High Priority
- NFR-23 (RESTful принципы) — Medium Priority
- NFR-24 (HTTP коды статуса) — High Priority

**Критерии приемки:**
- ✅ Реализовано 5 API эндпоинтов (POST, GET, PUT, track, stats)
- ✅ Все эндпоинты имеют валидацию входных данных
- ✅ Test coverage ≥ 80%
- ✅ Следование REST принципам
- ✅ Корректные HTTP статус коды

---

### HABIT-002: Стандартизация обработки ошибок 🔄

**Статус:** In Progress
**Релиз:** v1.1 (2025.10)

**Связанные NFR:**
- NFR-02 (Ошибки в формате RFC7807) — High Priority
- NFR-13 (Error Rate) — High Priority

**Критерии приемки:**
- [ ] Все ошибки возвращаются в едином формате RFC7807
- [ ] Маскирование PII в сообщениях об ошибках
- [ ] Добавление correlation ID для трассировки
- [ ] Error rate < 1% в production

---

### HABIT-003: Настройка CI/CD с security checks ✅

**Статус:** Completed (2025.09)
**Релиз:** v1.0

**Связанные NFR:**
- NFR-04 (Уязвимости зависимостей) — High Priority
- NFR-20 (Linting) — High Priority

**Критерии приемки:**
- ✅ CI pipeline с ruff, black, isort
- ✅ Pre-commit hooks настроены
- ✅ Автоматический запуск тестов
- ✅ Block direct push to main

---

### HABIT-025: Baseline performance tests ✅

**Статус:** Completed (2025.10)
**Релиз:** v1.0

**Связанные NFR:**
- NFR-07 (Время ответа GET /habits) — High Priority
- NFR-08 (Время ответа POST /habits) — High Priority
- NFR-09 (Время ответа GET /habits/stats) — High Priority

**Критерии приемки:**
- ✅ Performance тесты реализованы для всех key endpoints
- ✅ Метрики p50/p95/p99 измеряются и логируются
- ✅ NFR-07: GET /habits p95 = 1.93ms (target ≤200ms) ✅
- ✅ NFR-08: POST /habits p95 = 2.22ms (target ≤300ms) ✅
- ✅ NFR-09: GET stats p95 = 2.69ms (target ≤500ms) ✅
- ✅ Concurrent request simulation (50 requests, 100% success rate)

---

### HABIT-006: Настройка health check и monitoring 🔄

**Статус:** In Progress
**Релиз:** v1.1 (2025.10)

**Связанные NFR:**
- NFR-12 (API Uptime) — High Priority
- NFR-17 (Health Check эндпоинт) — High Priority

**Критерии приемки:**
- [ ] Health check endpoint реализован
- [ ] Response time < 50ms
- [ ] Uptime monitoring настроен
- [ ] Алерты на downtime > 1%

---

### HABIT-017: Интеграция Dependabot/Safety 📋

**Статус:** Planned
**Релиз:** v1.1 (2025.10)

**Связанные NFR:**
- NFR-04 (Уязвимости зависимостей) — High Priority
- NFR-22 (Dependency Updates) — Medium Priority

**Критерии приемки:**
- [ ] Dependabot настроен для автоматических PR
- [ ] Safety check интегрирован в CI
- [ ] SLA: Critical/High уязвимости устраняются за ≤ 7 дней
- [ ] Weekly автоматическая проверка зависимостей

---

### HABIT-020: Настройка нагрузочного тестирования 📋

**Статус:** Planned
**Релиз:** v1.2 (2025.11)

**Связанные NFR:**
- NFR-10 (Пропускная способность) — Medium Priority
- NFR-11 (Concurrent Users) — Medium Priority

**Критерии приемки:**
- [ ] Locust/k6 сценарии написаны
- [ ] Тесты на 100 RPS sustained load
- [ ] Тесты на 50 concurrent users
- [ ] Результаты включены в CI reporting

---

## 3. Release Roadmap с NFR Coverage

### v1.0 — MVP (Сентябрь-Октябрь 2025) ✅

**Фокус:** Основной функционал API и базовая производительность

**Реализованные NFR:**
- ✅ NFR-01: Валидация входных данных
- ✅ NFR-04: Уязвимости зависимостей (CI checks)
- ✅ NFR-07: Производительность GET /habits (p95 < 2ms ≪ 200ms target)
- ✅ NFR-08: Производительность POST /habits (p95 < 3ms ≪ 300ms target)
- ✅ NFR-09: Производительность GET stats (p95 < 3ms ≪ 500ms target)
- ✅ NFR-19: Test Coverage 93.6% (29 tests)
- ✅ NFR-20: Linting (ruff, black, isort)
- ✅ NFR-23: RESTful принципы
- ✅ NFR-24: HTTP коды статуса

**Delivered Stories:**
- HABIT-001: Реализация API эндпоинтов
- HABIT-003: CI/CD setup
- HABIT-025: Baseline performance tests

---

### v1.1 — Security & Reliability Improvements (Октябрь 2025) 🔄

**Фокус:** Безопасность и наблюдаемость

**Планируемые NFR:**
- 🔄 NFR-02: RFC7807 формат ошибок
- 🔄 NFR-06: HTTPS только
- 🔄 NFR-12: API Uptime 99%+
- 🔄 NFR-13: Error Rate < 1%
- 🔄 NFR-14: Graceful Degradation
- 🔄 NFR-17: Health Check
- 🔄 NFR-19: Test Coverage 90%+
- 🔄 NFR-21: Static Analysis (bandit, safety)

**Planned Stories:**
- HABIT-002: Стандартизация ошибок
- HABIT-006: Health check и monitoring
- HABIT-008: Увеличение test coverage
- HABIT-015: Улучшение валидации
- HABIT-017: Dependabot/Safety
- HABIT-018: Input Sanitization
- HABIT-024: Static analysis в CI

---

### v1.2 — Performance & Observability (Ноябрь 2025) 📋

**Фокус:** Производительность под нагрузкой и мониторинг

**Планируемые NFR:**
- 📋 NFR-03: Rate Limiting
- 📋 NFR-10: Пропускная способность 100 RPS
- 📋 NFR-11: 50 concurrent users
- 📋 NFR-15: Data Consistency
- 📋 NFR-16: Structured Logging
- 📋 NFR-25: OpenAPI документация

**Planned Stories:**
- HABIT-007: Structured logging
- HABIT-009: OpenAPI спецификация
- HABIT-016: Rate limiting middleware
- HABIT-019: TLS configuration
- HABIT-020: Load testing setup (Locust)
- HABIT-022: Data validation layer

---

### v1.3 — Advanced Monitoring (Декабрь 2025) 📋

**Фокус:** Продвинутая наблюдаемость

**Планируемые NFR:**
- 📋 NFR-18: Prometheus/OpenTelemetry метрики

**Planned Stories:**
- HABIT-023: Интеграция Prometheus/OpenTelemetry

---

## 4. Priority Distribution по Releases

| Release | High Priority NFRs | Medium Priority NFRs | Low Priority NFRs | Total NFRs |
|---------|-------------------|---------------------|------------------|------------|
| v1.0    | 9 (completed)     | 2 (completed)       | 0                | 11         |
| v1.1    | 8 (planned)       | 1 (planned)         | 0                | 9          |
| v1.2    | 1 (planned)       | 4 (planned)         | 0                | 5          |
| v1.3    | 0                 | 1 (planned)         | 0                | 1          |

---

## 5. NFR Verification Plan

### Automated Verification (CI/CD)

| NFR ID | Verification Method            | Tool/Framework        | Frequency     |
|--------|--------------------------------|-----------------------|---------------|
| NFR-01 | Unit tests                     | pytest                | Every commit  |
| NFR-02 | Integration tests              | pytest + TestClient   | Every commit  |
| NFR-04 | Dependency scanning            | safety, pip-audit     | Daily         |
| NFR-19 | Coverage reporting             | pytest-cov            | Every commit  |
| NFR-20 | Linting                        | ruff, black, isort    | Every commit  |
| NFR-21 | Static analysis                | bandit                | Every commit  |

### Manual Verification (Staging/Production)

| NFR ID | Verification Method            | Tool/Framework        | Frequency     |
|--------|--------------------------------|-----------------------|---------------|
| NFR-07 | Load testing                   | Locust/k6             | Weekly        |
| NFR-08 | Load testing                   | Locust/k6             | Weekly        |
| NFR-09 | Load testing                   | Locust/k6             | Weekly        |
| NFR-12 | Uptime monitoring              | Health checks         | Continuous    |
| NFR-13 | Error rate monitoring          | Application logs      | Continuous    |

---

## 7. Применение NFR к проекту

### 7.1 CI/CD отчёты

Реализация и проверка NFR осуществляется через расширенный CI/CD pipeline:

**Security Checks (NFR-04, NFR-21):**
- `safety check` — сканирование зависимостей на уязвимости
- `bandit` — статический анализ безопасности кода
- Отчёты в формате JSON и markdown в GitHub Actions summary

**Code Quality (NFR-19, NFR-20):**
- `pytest-cov` — измерение покрытия тестами (≥80%)
- `ruff`, `black`, `isort` — проверка стиля кода
- Coverage report в XML/HTML формате

**Performance (NFR-07, NFR-08, NFR-09):**
- Baseline performance tests через pytest
- Locust для нагрузочного тестирования
- Метрики p95/p99 в отчётах CI

### 7.2 Дашборды мониторинга

**Planned для v1.2-v1.3:**
- Prometheus для сбора метрик производительности
- Grafana dashboards:
  - API response times (p50, p95, p99)
  - Request rate и throughput
  - Error rate по эндпоинтам
  - System resources (CPU, memory)
- OpenTelemetry для distributed tracing

**Current State (v1.0):**
- Health check endpoint `/health`
- Application logs с структурированным форматом (planned v1.2)
- CI/CD pipeline metrics

### 7.3 Логи тестов

**Automated Test Logging:**
- Pytest verbose output в CI artifacts
- Coverage reports (HTML/XML) сохраняются как artifacts
- Security scan results (safety, bandit) в JSON формате
- Load test results с метриками производительности

**Test Reports Location:**
- GitHub Actions: Summary tab для каждого workflow run
- Artifacts: coverage.xml, bandit-report.json
- Local: htmlcov/ directory после `pytest --cov`

---

## 8. Включение в Backlog/Roadmap

### 8.1 Приоритизация и сроки

Все NFR включены в product backlog с чётким приоритетом и релизными окнами:

**v1.1 (2025-10-31) - High Priority:**
- NFR-02: RFC7807 error format — HABIT-002
- NFR-04: Dependency scanning — HABIT-017
- NFR-05: Input sanitization — HABIT-018
- NFR-12: API Uptime — HABIT-006
- NFR-17: Health check — HABIT-006
- NFR-19: Test coverage 90% — HABIT-008
- NFR-21: Static analysis — HABIT-024

**v1.2 (2025-11-30) - Medium Priority:**
- NFR-03: Rate limiting — HABIT-016
- NFR-07: GET /habits performance — HABIT-004
- NFR-09: GET /stats performance — HABIT-005
- NFR-16: Structured logging — HABIT-007
- NFR-25: API documentation — HABIT-009

**v1.3 (2025-12-31) - Advanced Features:**
- NFR-18: Prometheus integration — HABIT-023
- Advanced monitoring and alerting

### 8.2 Назначенные исполнители

| Роль              | Ответственность                           | NFR Coverage        |
|-------------------|-------------------------------------------|---------------------|
| Backend Developer | API implementation, optimization          | NFR-01 to NFR-15    |
| DevOps Engineer   | CI/CD, monitoring, infrastructure         | NFR-04, NFR-18, NFR-21 |
| QA Engineer       | Testing, coverage, load testing           | NFR-19, NFR-07-11   |
| Tech Lead         | Architecture, security, NFR governance    | All NFRs            |

### 8.3 Трекинг прогресса

**Milestone Structure:**
- v1.1: 9 issues linked to NFRs
- v1.2: 7 issues linked to NFRs
- v1.3: 3 issues linked to NFRs

**Issue Templates:**
- Шаблоны созданы в `.github/ISSUE_TEMPLATE/`
- Каждый issue содержит:
  - NFR ID и ссылку на NFR.md
  - Метрики и пороги
  - Acceptance criteria
  - Verification plan
  - Estimate и assignee

**Документация:**
- Полный backlog: `docs/BACKLOG.md`
- Примеры issues: `docs/EXAMPLE_ISSUES.md`
- NFR документация: `docs/security-nfr/`

### 8.4 Definition of Done

Задачи по NFR считаются выполненными когда:

- [ ] NFR метрика достигла целевого порога
- [ ] CI/CD проверки проходят
- [ ] BDD сценарии (если есть) выполняются успешно
- [ ] Документация обновлена (NFR_TRACEABILITY.md)
- [ ] Monitoring/logging настроены
- [ ] Code review пройден
- [ ] Тесты добавлены (coverage ≥ 80%)

### 8.5 Review и Ретроспектива

**Frequency:** Каждые 2 недели (sprint review)

**Процесс:**
1. Проверка выполнения NFR из текущего спринта
2. Анализ метрик из CI/CD
3. Обновление NFR_TRACEABILITY.md
4. Корректировка приоритетов при необходимости
5. Планирование следующего спринта

---

## Revision History

| Дата       | Версия | Автор | Изменения                                     |
|------------|--------|-------|-----------------------------------------------|
| 2025-10-05 | 1.2    | Team  | Обновлены статусы NFR-07/08/09: Completed. Добавлена задача HABIT-025 (performance tests) |
| 2025-10-05 | 1.1    | Team  | Добавлены секции применения и backlog         |
| 2025-10-05 | 1.0    | Team  | Первая версия трассируемости NFR              |
