# BDD Scenarios for Non-Functional Requirements

## Введение

Данный документ содержит BDD сценарии для проверки ключевых нефункциональных требований проекта Habit Tracker API в формате Gherkin.

**Дата:** 2025-10-05
**Версия:** 1.0

---

## Feature: Security — Валидация входных данных (NFR-01)

### Scenario: Создание привычки с валидацией данных
```gherkin
Given API сервис запущен и доступен
When клиент отправляет POST /habits с валидными данными
  """json
  {
    "name": "Пить воду",
    "description": "Выпивать 8 стаканов воды в день",
    "frequency": "daily"
  }
  """
Then ответ должен иметь статус 200 OK
And привычка должна быть создана с корректными данными
And response time должен быть < 150ms
```

### Scenario: Отклонение невалидных данных при создании привычки
```gherkin
Given API сервис запущен и доступен
When клиент отправляет POST /habits с пустым именем
  """json
  {
    "name": "",
    "description": "Описание",
    "frequency": "daily"
  }
  """
Then ответ должен иметь статус 422 Unprocessable Entity
And тело ответа должно содержать структурированную ошибку
  """json
  {
    "error": {
      "code": "validation_error",
      "message": "Habit name cannot be empty"
    }
  }
  """
And PII данные НЕ должны быть в логах
```

### Scenario: Защита от SQL injection
```gherkin
Given API сервис запущен и доступен
When клиент отправляет POST /habits с SQL injection payload
  """json
  {
    "name": "'; DROP TABLE habits; --",
    "description": "test"
  }
  """
Then ответ должен иметь статус 422 или 400
And SQL команды НЕ должны быть выполнены
And данные должны быть sanitized
```

---

## Feature: Performance — Время ответа GET /habits (NFR-07)

### Scenario: Производительность получения списка привычек под нагрузкой
```gherkin
Given API сервис развернут на staging окружении
And база данных содержит 100 привычек для тестового пользователя
When выполняется нагрузочный тест с 50 RPS в течение 5 минут
Then p95 времени ответа для GET /habits должен быть ≤ 100ms
And p99 времени ответа должен быть ≤ 150ms
And error rate должен быть < 1%
```

### Scenario: Производительность при пиковой нагрузке
```gherkin
Given API сервис развернут на staging окружении
When выполняется spike тест с резким увеличением до 100 RPS
Then сервис должен оставаться отзывчивым
And p95 времени ответа НЕ должен превышать 200ms
And 0 запросов должны завершиться timeout'ом
```

### Scenario Outline: Время ответа различных эндпоинтов
```gherkin
Given API сервис запущен
When клиент выполняет <method> запрос к <endpoint>
Then время ответа должно быть < <max_response_time>ms

Examples:
  | method | endpoint                 | max_response_time |
  | GET    | /health                  | 50                |
  | GET    | /habits                  | 100               |
  | POST   | /habits                  | 150               |
  | GET    | /habits/1/stats          | 200               |
  | POST   | /habits/1/track          | 150               |
  | PUT    | /habits/1                | 150               |
```

---

## Feature: Security — Обработка ошибок RFC7807 (NFR-02)

### Scenario: Стандартизированный формат ошибок
```gherkin
Given API сервис запущен
When происходит ошибка валидации на любом эндпоинте
Then ответ должен содержать поле "error"
And поле "error" должно содержать "code" и "message"
And формат должен соответствовать RFC7807
And response должен содержать соответствующий HTTP статус код
```

### Scenario: Маскирование чувствительных данных в ошибках
```gherkin
Given API сервис запущен
When происходит ошибка с потенциальными PII данными
Then сообщение об ошибке НЕ должно содержать:
  | PII Type      |
  | email         |
  | phone number  |
  | internal IDs  |
  | stack traces  |
And все PII должны быть замаскированы символом "*"
```

---

## Feature: Reliability — API Uptime (NFR-12)

### Scenario: Health check эндпоинт всегда доступен
```gherkin
Given API сервис развернут на staging
When выполняется непрерывный мониторинг в течение 24 часов
Then GET /health должен возвращать 200 OK ≥ 99% времени
And среднее время ответа health check должно быть < 50ms
And downtime НЕ должен превышать 14.4 минут в день
```

### Scenario: Graceful degradation при сбоях
```gherkin
Given API сервис работает нормально
When происходит внутренняя ошибка в одном из модулей
Then сервис должен вернуть 500 Internal Server Error
And сообщение об ошибке должно быть структурированным
And другие эндпоинты должны продолжать работать
And ошибка должна быть залогирована с correlation ID
```

---

## Feature: Security — Уязвимости зависимостей (NFR-04)

### Scenario: Отсутствие критических уязвимостей в production
```gherkin
Given проект готов к deployment в production
When выполняется SCA (Software Composition Analysis)
Then количество Critical уязвимостей должно быть = 0
And количество High уязвимостей должно быть = 0
And все Medium уязвимости должны иметь plan на устранение
```

### Scenario: Быстрое устранение обнаруженных уязвимостей
```gherkin
Given в зависимостях обнаружена Critical/High уязвимость
When создается issue для устранения
Then уязвимость должна быть устранена в течение ≤ 7 дней
And patch должен быть протестирован
And обновление должно быть задеплоено
```

---

## Feature: Performance — Rate Limiting (NFR-03)

### Scenario: Защита от abuse через rate limiting
```gherkin
Given API сервис запущен с rate limiting
When один IP адрес отправляет > 100 запросов в минуту
Then запросы сверх лимита должны получить 429 Too Many Requests
And response должен содержать заголовок Retry-After
And легитимные запросы от других IP НЕ должны быть затронуты
```

### Scenario: Rate limit для разных эндпоинтов
```gherkin
Given API сервис запущен
When клиент превышает rate limit на POST /habits
Then должен быть возвращен 429 статус код
And тело ответа должно объяснять причину:
  """json
  {
    "error": {
      "code": "rate_limit_exceeded",
      "message": "Too many requests. Please try again later.",
      "retry_after": 60
    }
  }
  """
```

---

## Feature: Code Quality — Test Coverage (NFR-19)

### Scenario: Минимальное покрытие тестами
```gherkin
Given проект готов к merge в main
When выполняется pytest с coverage
Then общее покрытие должно быть ≥ 80%
And все критические модули должны иметь ≥ 90% coverage
And CI pipeline должен fail если coverage < 80%
```

### Scenario: Все новые фичи покрыты тестами
```gherkin
Given добавляется новый API эндпоинт
When создается Pull Request
Then новый код должен иметь ≥ 90% test coverage
And должны присутствовать:
  | Test Type           |
  | unit tests          |
  | integration tests   |
  | error case tests    |
And CI должен блокировать merge при недостаточном coverage
```

---

## Negative Scenarios — Граничные случаи и отказоустойчивость

### Scenario: Обработка экстремально больших входных данных
```gherkin
Given API сервис запущен
When клиент отправляет POST /habits с очень длинным description (10,000 символов)
Then ответ должен иметь статус 422
And сообщение должно указывать на превышение лимита
And сервис НЕ должен упасть или зависнуть
```

### Scenario: Concurrent requests к одному ресурсу
```gherkin
Given привычка с ID=1 существует
When 50 клиентов одновременно отправляют PUT /habits/1
Then все запросы должны быть обработаны корректно
And данные НЕ должны быть повреждены (race condition)
And все ответы должны иметь корректный статус код
```

### Scenario: Поведение при недоступности зависимостей
```gherkin
Given API сервис запущен
When база данных становится недоступной
Then новые запросы должны получать 503 Service Unavailable
And GET /health должен возвращать статус "degraded"
And сервис должен автоматически восстановиться при возвращении БД
```

### Scenario: Обработка некорректных дат
```gherkin
Given API сервис запущен
When клиент отправляет POST /habits/1/track с некорректной датой
  """json
  {
    "completed_at": "2025-13-45"
  }
  """
Then ответ должен иметь статус 422
And сообщение должно содержать "Invalid date format"
And сервис НЕ должен записать некорректные данные
```

---

## Revision History

| Дата       | Версия | Автор | Изменения                          |
|------------|--------|-------|------------------------------------|
| 2025-10-05 | 1.0    | Team  | Первая версия BDD сценариев NFR    |
