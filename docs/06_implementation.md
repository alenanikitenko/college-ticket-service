# УП6–УП12. Реализация и проверка

Все проверки автоматические: `python -m pytest` → **134 passed**. Ниже для каждого этапа: обязательный результат из задания, где он реализован и какой тест его подтверждает.

## УП6. Каркас приложения и конфигурация

| Обязательный результат | Реализация | Тест |
|------------------------|------------|------|
| Python‑пакет `app`, экземпляр FastAPI | `app/main.py` → `create_app()`, `app = create_app()` | `test_startup_handler_runs_and_openapi_is_available` |
| Настройки через переменные окружения | `app/core/config.py` (`load_settings`, `get_settings`), `.env.example` | `test_dev_config_has_defaults_and_reads_variables`, `test_dotenv_file_is_loaded` |
| `GET /health` → 200 `{"status":"ok"}` | `app/routers/health.py` (дополнительно делает `SELECT 1`, при сбое БД — 503) | `test_health_returns_200_status_ok` |
| Отсутствующая обязательная переменная в test‑конфигурации → понятное сообщение | `ConfigError`: «Не задана обязательная переменная окружения: SECRET_KEY (APP_ENV=test)…» | `test_missing_required_variable_in_test_config_gives_clear_message`, `test_missing_database_url_in_test_config_is_reported`, `test_python_m_app_reports_config_error` |
| Обработчик запуска | `lifespan` → `_on_startup()`: проверка соединения с БД, опциональное создание первого администратора, `app.state.started_at` | `test_startup_handler_runs_and_openapi_is_available` |
| `requirements.txt` | `requirements.txt` | — |

Файл тестов: `tests/test_app_config.py` — 12 тестов (три обязательных идут первыми).

## УП7. Модели SQLAlchemy

| Обязательный результат | Реализация | Тест |
|------------------------|------------|------|
| 5 ORM‑моделей с полями и связями из ТЗ | `app/models/{user,category,ticket,comment,audit_event}.py` | `test_metadata_contains_exactly_five_tables`, `test_relationships_defaults_and_timestamps` |
| Роли и статусы — Enum | `app/models/enums.py`: `UserRole`, `TicketStatus`, `AuditAction`; в БД — VARCHAR + CHECK | `test_enums_have_required_values`, `test_invalid_enum_value_is_rejected` |
| Все PK / FK / unique | PK `id` во всех таблицах; FK с `ON DELETE`; unique `users.email`, `categories.name` | `test_every_table_has_integer_id_primary_key`, `test_foreign_keys_and_on_delete_rules`, `test_unique_constraints_and_nullability` |
| Тест создаёт схему во временной SQLite | `Base.metadata.create_all` в `tmp_path` | `test_schema_is_created_in_temporary_sqlite` |

Дополнительно: внешние ключи в SQLite включены (`PRAGMA foreign_keys=ON`) — `test_foreign_keys_are_enforced_in_sqlite`; CHECK `priority BETWEEN 1 AND 5` — `test_priority_check_constraint`.

## УП8. Миграции Alembic

| Обязательный результат | Реализация | Тест |
|------------------------|------------|------|
| Начальная миграция | `migrations/versions/0001_initial_schema.py` | `test_upgrade_head_creates_schema_and_three_categories` |
| Миграция категорий «IT», «Учебный процесс», «Хозяйственная часть» | `migrations/versions/0002_seed_categories.py` | то же |
| `upgrade head` создаёт схему и 3 категории | — | `test_upgrade_head_creates_schema_and_three_categories` |
| `downgrade` удаляет изменения; повторный `upgrade` без ручной правки | `downgrade()` в обеих миграциях | `test_downgrade_removes_changes_and_upgrade_again_works` |

Дополнительно: `test_migrations_match_orm_models` — после `upgrade head` autogenerate не находит расхождений между БД и моделями; `test_seed_migration_is_idempotent_with_existing_category`.

## УП9. Репозитории и транзакции

| Обязательный результат | Реализация | Тест |
|------------------------|------------|------|
| Базовые операции для 5 сущностей | `app/repositories/*.py` (`add`, `get`, `list`, `count`, `delete` + специфичные запросы) | `test_*_repository_*` |
| 5 репозиториев не импортируют FastAPI | проверка AST каждого файла; там же запрет `commit`/`rollback` | `test_five_repositories_exist`, `test_repository_does_not_import_fastapi_and_does_not_commit` |
| `commit` в сервисе, `rollback` при исключении | `app/services/base.py` → `transaction()` | `test_transaction_helper_rolls_back_on_exception` |
| Тест отката: нет частично записанных данных | `TicketService.create_ticket` пишет заявку и аудит в одной транзакции; в тесте запись аудита падает | `test_rollback_leaves_no_partial_data` |

## УП10. Схемы Pydantic и валидация

| Ограничение | Граничные значения в тесте |
|-------------|----------------------------|
| `email` валиден | 3 валидных, 6 невалидных адресов |
| `full_name` 2–100 | 1 ✗, 2 ✓, 100 ✓, 101 ✗, «   » ✗ |
| `title` 3–100 | 2 ✗, 3 ✓, 100 ✓, 101 ✗ |
| `description` 1–2000 | 0 ✗, 1 ✓, 2000 ✓, 2001 ✗ |
| `priority` 1–5 | 0 ✗, 1 ✓, 5 ✓, 6 ✗, по умолчанию 3 |
| `text` комментария 1–1000 | 0 ✗, 1 ✓, 1000 ✓, 1001 ✗ |
| `password` 8–128 | 7 ✗, 8 ✓, 128 ✓, 129 ✗ |

`password_hash` отсутствует во всех выходных схемах (`OUTPUT_SCHEMAS`) — `test_output_schema_has_no_password_fields`, `test_no_exported_schema_exposes_password_hash`, `test_user_read_from_orm_drops_password_hash`. Файл: `tests/test_schemas.py` (47 тестов).

## УП11. Регистрация и хэширование пароля

| Обязательный результат | Тест |
|------------------------|------|
| Регистрация `user1@college.edu` успешна, 201, без хэша, роль `student` | `test_register_user1_returns_201_without_hash`, `test_default_role_is_student` |
| Повторный email → 409 | `test_duplicate_email_returns_409_and_does_not_create_user`, `test_duplicate_email_is_case_insensitive` |
| Пароль не хранится открыто и проверяется функцией `verify` | `test_password_is_stored_only_as_strong_hash`, `test_same_password_gives_different_hashes` |

Хэш: `hashlib.scrypt` (n=2^14, r=8, p=1, соль 16 байт, длина 64 байта), формат `scrypt$n$r$p$salt$hash`, сравнение `hmac.compare_digest`. Роль клиент выбрать не может (`extra="forbid"` → 422) — `test_client_cannot_choose_role`.

## УП12. Вход, токен и текущий пользователь

| Обязательный результат | Тест |
|------------------------|------|
| Верный вход → 200 и token | `test_valid_login_returns_200_and_token` |
| Токен содержит `user_id` (`sub`) и `role`, имеет срок действия (`exp`) | `test_token_contains_user_id_role_and_expiry` |
| Неверный пароль → 401 | `test_wrong_password_returns_401`, `test_unknown_email_returns_same_401` |
| Неактивный пользователь не входит | `test_inactive_user_cannot_login` (403 `user_inactive`) |
| `/users/me` без токена → 401 | `test_users_me_without_token_returns_401` |
| `/users/me` с токеном → профиль без `password_hash` | `test_users_me_with_token_returns_profile_without_hash` |

Дополнительно: просроченный, поддельный и «мусорный» токены → 401; токен деактивированного пользователя перестаёт работать.

## Ручная проверка через Swagger UI

1. `python -m app` → открыть http://127.0.0.1:8000/docs.
2. `POST /auth/register` → `{"email": "user1@college.edu", "full_name": "Иван Петров", "password": "Secret123!"}` → **201**.
3. `POST /auth/login` с теми же email/паролем → **200**, скопировать `access_token`.
4. Кнопка **Authorize** → вставить токен → `GET /users/me` → **200**, профиль без `password_hash`.
