# УП5. Контракт API

* Формат: `application/json; charset=utf-8`. Время — ISO 8601 в UTC.
* Аутентификация: заголовок `Authorization: Bearer <JWT>`. Токен выдаёт `POST /auth/login`, содержит `sub` (id пользователя), `role` и `exp` (срок действия, по умолчанию 60 минут).
* Документация генерируется автоматически: Swagger UI — `GET /docs`, схема OpenAPI 3 — `GET /openapi.json`.
* Роли: **S** — student, **O** — operator, **A** — admin, **все** — любой авторизованный пользователь, **гость** — без токена.

## Единый формат ошибки

Любая ошибка (4xx/5xx), включая ошибки валидации FastAPI, возвращается в одной структуре — схема OpenAPI `ErrorResponse`:

```json
{
  "error": {
    "code": "conflict",
    "message": "Пользователь с таким email уже существует",
    "details": null
  }
}
```

Для `422` поле `details` — список нарушений:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Ошибка валидации входных данных",
    "details": [{"field": "body.title", "message": "String should have at least 3 characters"}]
  }
}
```

| HTTP | `error.code` | Когда |
|------|--------------|-------|
| 400 | `bad_request` | Некорректный запрос, не подходящий под другие коды |
| 401 | `unauthorized` | Нет токена, токен неверный или истёк, неверный email/пароль |
| 403 | `forbidden` | Роль или владелец не позволяют операцию |
| 403 | `user_inactive` | Вход пользователя с `is_active=false` |
| 404 | `not_found` | Ресурс с таким id не существует |
| 409 | `conflict` | Нарушение уникальности (email, имя категории) или удаление категории с заявками |
| 409 | `invalid_transition` | Недопустимый переход статуса |
| 422 | `validation_error` | Тело/параметры не прошли валидацию Pydantic |
| 422 | `invalid_assignee` | Назначаемый пользователь не является активным оператором |
| 503 | `service_unavailable` | База данных недоступна (`/health`) |

## Операции

| № | Метод | Путь | Роль | Тело запроса → ответ | Успех | Ошибки |
|---|-------|------|------|----------------------|-------|--------|
| 1 | GET | `/health` | гость | — → `{"status":"ok"}` | **200** | 503 |
| 2 | POST | `/auth/register` | гость | `UserRegister` → `UserRead` | **201** | 409, 422 |
| 3 | POST | `/auth/login` | гость | `LoginRequest` → `TokenResponse` | **200** | 401, 403, 422 |
| 4 | GET | `/users/me` | все | — → `UserRead` | **200** | 401 |
| 5 | GET | `/users` | A | query `role`, `is_active` → `UserRead[]` | **200** | 401, 403 |
| 6 | PATCH | `/users/{id}` | A | `UserAdminUpdate` → `UserRead` | **200** | 401, 403, 404, 422 |
| 7 | GET | `/categories` | все | — → `CategoryRead[]` | **200** | 401 |
| 8 | POST | `/categories` | A | `CategoryCreate` → `CategoryRead` | **201** | 401, 403, 409, 422 |
| 9 | PUT | `/categories/{id}` | A | `CategoryUpdate` → `CategoryRead` | **200** | 403, 404, 409, 422 |
| 10 | DELETE | `/categories/{id}` | A | — → пусто | **204** | 403, 404, 409 |
| 11 | POST | `/tickets` | S | `TicketCreate` → `TicketRead` | **201** | 401, 403, 404 (категория), 422 |
| 12 | GET | `/tickets` | все (с учётом роли) | query `status`, `priority`, `category_id`, `assignee_id`, `limit` (1–100, по умолч. 20), `offset` → `TicketRead[]` | **200** | 401, 422 |
| 13 | GET | `/tickets/{id}` | все (с учётом роли) | — → `TicketRead` | **200** | 401, 403, 404 |
| 14 | PATCH | `/tickets/{id}/assign` | A; O — только на себя | `TicketAssign` → `TicketRead` | **200** | 403, 404, 409 (заявка закрыта), 422 |
| 15 | PATCH | `/tickets/{id}/status` | O (исполнитель), A; S — только `resolved→closed` своей заявки | `TicketStatusUpdate` → `TicketRead` | **200** | 403, 404, 409, 422 |
| 16 | POST | `/tickets/{id}/comments` | автор заявки, исполнитель, A | `CommentCreate` → `CommentRead` | **201** | 401, 403, 404, 422 |
| 17 | GET | `/tickets/{id}/comments` | автор заявки, исполнитель, A | — → `CommentRead[]` | **200** | 401, 403, 404 |
| 18 | GET | `/tickets/{id}/audit` | O, A | — → `AuditEventRead[]` (по возрастанию `created_at`) | **200** | 401, 403, 404 |
| 19 | GET | `/reports/summary` | A | — → `ReportSummary` | **200** | 401, 403 |
| 20 | WS | `/ws/notifications?token=<JWT>` | все | сервер отправляет `{"event": "...", "ticket_id": N, ...}` | **101** (Switching Protocols) | закрытие с кодом **1008** при неверном токене |
| 21 | GET | `/openapi.json`, `/docs` | гость | — → схема OpenAPI / Swagger UI | **200** | — |

**Итого 21 операция** (минимум по заданию — 15).

### Видимость заявок по ролям (операции 12, 13)

| Роль | Видит |
|------|-------|
| student | только свои заявки (`author_id = текущий пользователь`); чужая по id → 403 |
| operator | заявки, назначенные на него, и все заявки без исполнителя в статусе `new` |
| admin | все заявки |

### Правила смены статуса (операция 15)

| Переход | Кто может |
|---------|-----------|
| `new → in_progress` | назначенный оператор, admin (у заявки должен быть исполнитель, иначе 409) |
| `in_progress → resolved` | назначенный оператор, admin |
| `resolved → closed` | автор‑студент, admin |
| любой другой | никто → **409** `invalid_transition` |

Каждое изменение пишет событие в `audit_events` и рассылает WebSocket‑уведомление `ticket_updated`.

## Схемы OpenAPI (components/schemas)

| Схема | Поля и ограничения | Где |
|-------|--------------------|-----|
| `UserRegister` | `email`: EmailStr; `full_name`: str 2–100; `password`: str 8–128. Лишние поля (например `role`) запрещены → 422 | тело 2 |
| `LoginRequest` | `email`: EmailStr; `password`: str 1–128 | тело 3 |
| `TokenResponse` | `access_token`: str; `token_type`: `"bearer"`; `expires_in`: int (секунды) | ответ 3 |
| `UserRead` | `id`, `email`, `full_name`, `role`, `is_active`, `created_at` — **без `password_hash`** | ответы 2, 4, 5, 6 |
| `UserAdminUpdate` | `role`?: UserRole; `is_active`?: bool | тело 6 |
| `CategoryCreate` / `CategoryUpdate` | `name`: str 2–100 | тела 8, 9 |
| `CategoryRead` | `id`, `name` | ответы 7–9 |
| `TicketCreate` | `title`: str 3–100; `description`: str 1–2000; `priority`: int 1–5 (по умолч. 3); `category_id`: int ≥ 1 | тело 11 |
| `TicketRead` | `id`, `title`, `description`, `status`, `priority`, `author_id`, `assignee_id` (nullable), `category_id`, `created_at`, `updated_at` | ответы 11–15 |
| `TicketAssign` | `assignee_id`: int ≥ 1 | тело 14 |
| `TicketStatusUpdate` | `status`: TicketStatus | тело 15 |
| `CommentCreate` | `text`: str 1–1000 | тело 16 |
| `CommentRead` | `id`, `ticket_id`, `author_id`, `text`, `created_at` | ответы 16, 17 |
| `AuditEventRead` | `id`, `ticket_id`, `actor_id`, `action`, `created_at` | ответ 18 |
| `ReportSummary` | `total`: int; `by_status`: {status: int}; `by_priority`: {"1".."5": int}; `by_category`: {name: int} | ответ 19 |
| `ErrorResponse` | `error`: {`code`: str, `message`: str, `details`: any \| null} | все ошибки |
| `UserRole` | enum `student`, `operator`, `admin` | — |
| `TicketStatus` | enum `new`, `in_progress`, `resolved`, `closed` | — |

## Примеры

```http
POST /auth/register
Content-Type: application/json

{"email": "user1@college.edu", "full_name": "Иван Петров", "password": "Secret123!"}
```
```http
HTTP/1.1 201 Created

{"id": 1, "email": "user1@college.edu", "full_name": "Иван Петров",
 "role": "student", "is_active": true, "created_at": "2026-10-24T09:00:00Z"}
```

```http
POST /auth/login
Content-Type: application/json

{"email": "user1@college.edu", "password": "Secret123!"}
```
```http
HTTP/1.1 200 OK

{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 3600}
```
