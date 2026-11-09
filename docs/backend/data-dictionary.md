# Dicionário de dados gerado

Extraído do metadata SQLAlchemy, sem consultar o banco. As migrações Alembic determinam a evolução do schema instalado. Tipos exibidos são os declarados pelo ORM; o dialeto pode adaptá-los.

PK = chave primária. FK = chave estrangeira. Campos nullable aceitam ausência; isso não autoriza omitir campos exigidos pela API.

## `audit`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `actor` | `VARCHAR(100)` | não | — | — |
| `action` | `VARCHAR(100)` | não | — | — |
| `detail` | `JSON` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

## `authors`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `VARCHAR(200)` | não | sim | — |
| `name` | `VARCHAR(500)` | não | — | — |
| `normalized_name` | `VARCHAR(500)` | não | — | — |
| `orcid` | `VARCHAR(30)` | sim | — | — |

Índices declarados no ORM: `ix_authors_normalized_name`, `ix_authors_orcid`.

## `calendar_fires`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `schedule_id` | `INTEGER` | não | — | calendar_schedules.id |
| `scheduled_at` | `DATETIME` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `job_id` | `INTEGER` | sim | — | — |
| `message` | `TEXT` | não | — | — |

Unicidade adicional: `schedule_id, scheduled_at`.

## `calendar_schedules`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `owner_id` | `INTEGER` | não | — | users.id |
| `name` | `VARCHAR(100)` | não | — | — |
| `target` | `VARCHAR(30)` | não | — | — |
| `target_id` | `INTEGER` | sim | — | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `params` | `JSON` | não | — | — |
| `cron` | `VARCHAR(100)` | não | — | — |
| `timezone` | `VARCHAR(100)` | não | — | — |
| `next_at` | `DATETIME` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |

Índices declarados no ORM: `ix_calendar_schedules_next_at`.

## `data_changes`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `run_id` | `INTEGER` | não | — | runs.id |
| `source` | `VARCHAR(30)` | não | — | — |
| `entity_id` | `VARCHAR(400)` | não | — | — |
| `field` | `VARCHAR(80)` | não | — | — |
| `before` | `JSON` | sim | — | — |
| `after` | `JSON` | sim | — | — |
| `created_at` | `DATETIME` | não | — | — |

Índices declarados no ORM: `ix_data_changes_entity_id`, `ix_data_changes_run_id`, `ix_data_changes_source`.

## `datasets`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `VARCHAR(200)` | não | sim | — |
| `title` | `TEXT` | não | — | — |
| `portal` | `VARCHAR(100)` | não | — | — |
| `url` | `TEXT` | não | — | — |
| `modified` | `VARCHAR(100)` | não | — | — |
| `resources` | `JSON` | não | — | — |
| `fingerprint` | `VARCHAR(64)` | não | — | — |
| `fetched_at` | `DATETIME` | não | — | — |

## `deliveries`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `webhook_id` | `INTEGER` | não | — | webhooks.id |
| `event_id` | `INTEGER` | não | — | events.id |
| `status` | `VARCHAR(20)` | não | — | — |
| `attempts` | `INTEGER` | não | — | — |
| `next_at` | `DATETIME` | não | — | — |
| `message` | `VARCHAR(200)` | não | — | — |

Unicidade adicional: `webhook_id, event_id`.

## `events`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `dedupe_key` | `VARCHAR(300)` | não | — | — |
| `kind` | `VARCHAR(30)` | não | — | — |
| `title` | `TEXT` | não | — | — |
| `payload` | `JSON` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

Unicidade adicional: `dedupe_key`.

## `executions`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `started_at` | `DATETIME` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `records` | `INTEGER` | não | — | — |
| `duration_ms` | `INTEGER` | não | — | — |
| `message` | `VARCHAR(500)` | não | — | — |

## `favorites`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `user_id` | `INTEGER` | não | sim | users.id |
| `kind` | `VARCHAR(30)` | não | sim | — |
| `entity_id` | `VARCHAR(400)` | não | sim | — |
| `created_at` | `DATETIME` | não | — | — |

## `incidents`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `title` | `VARCHAR(300)` | não | — | — |
| `detail` | `TEXT` | não | — | — |
| `status` | `VARCHAR(20)` | não | — | — |
| `active_key` | `VARCHAR(200)` | sim | — | — |
| `created_at` | `DATETIME` | não | — | — |
| `resolved_at` | `DATETIME` | sim | — | — |

Unicidade adicional: `active_key`.

## `institution_fields`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `institution_id` | `VARCHAR(200)` | não | sim | institutions.id |
| `field` | `VARCHAR(30)` | não | sim | — |
| `value` | `VARCHAR(250)` | não | sim | — |
| `label` | `VARCHAR(250)` | não | — | — |

Índices declarados no ORM: `ix_institution_fields_value`.

## `institution_profiles`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `institution_id` | `VARCHAR(200)` | não | sim | institutions.id |
| `watched` | `BOOLEAN` | não | — | — |
| `data` | `JSON` | não | — | — |
| `fetched_at` | `DATETIME` | sim | — | — |

## `institutions`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `VARCHAR(200)` | não | sim | — |
| `name` | `VARCHAR(500)` | não | — | — |
| `country` | `VARCHAR(100)` | não | — | — |
| `source` | `VARCHAR(50)` | não | — | — |

## `login_limits`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `key` | `VARCHAR(64)` | não | sim | — |
| `count` | `INTEGER` | não | — | — |
| `until` | `DATETIME` | não | — | — |

## `monitor_checks`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `target_id` | `INTEGER` | não | — | monitor_targets.id |
| `active_key` | `VARCHAR(100)` | sim | — | — |
| `state` | `VARCHAR(30)` | não | — | — |
| `outcome` | `VARCHAR(40)` | não | — | — |
| `ok` | `BOOLEAN` | sim | — | — |
| `message` | `TEXT` | não | — | — |
| `http_status` | `INTEGER` | sim | — | — |
| `final_url` | `TEXT` | não | — | — |
| `method` | `VARCHAR(10)` | não | — | — |
| `duration_ms` | `INTEGER` | não | — | — |
| `timings` | `JSON` | não | — | — |
| `redirects` | `JSON` | não | — | — |
| `tls` | `JSON` | não | — | — |
| `actor` | `VARCHAR(100)` | não | — | — |
| `manual` | `BOOLEAN` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |
| `started_at` | `DATETIME` | sim | — | — |
| `finished_at` | `DATETIME` | sim | — | — |
| `lease` | `VARCHAR(40)` | não | — | — |

Unicidade adicional: `active_key`.

Índices declarados no ORM: `ix_monitor_checks_state`, `ix_monitor_checks_target_id`.

## `monitor_config`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `enabled` | `BOOLEAN` | não | — | — |
| `discovery` | `BOOLEAN` | não | — | — |
| `per_day` | `INTEGER` | não | — | — |
| `per_host_minute` | `INTEGER` | não | — | — |
| `retention_days` | `INTEGER` | não | — | — |
| `next_discovery` | `DATETIME` | não | — | — |

## `monitor_references`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `target_id` | `INTEGER` | não | sim | monitor_targets.id |
| `kind` | `VARCHAR(30)` | não | sim | — |
| `entity_id` | `VARCHAR(400)` | não | sim | — |
| `role` | `VARCHAR(100)` | não | sim | — |
| `title` | `VARCHAR(500)` | não | — | — |

## `monitor_targets`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `url_hash` | `VARCHAR(64)` | não | — | — |
| `url` | `TEXT` | não | — | — |
| `host` | `VARCHAR(253)` | não | — | — |
| `name` | `VARCHAR(300)` | não | — | — |
| `kind` | `VARCHAR(30)` | não | — | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `expected_type` | `VARCHAR(20)` | não | — | — |
| `managed` | `BOOLEAN` | não | — | — |
| `archived` | `BOOLEAN` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |
| `interval_minutes` | `INTEGER` | não | — | — |
| `next_at` | `DATETIME` | não | — | — |
| `status` | `VARCHAR(40)` | não | — | — |
| `checked_at` | `DATETIME` | sim | — | — |
| `last_check_id` | `INTEGER` | sim | — | — |
| `failures` | `INTEGER` | não | — | — |
| `recoveries` | `INTEGER` | não | — | — |
| `alerts` | `BOOLEAN` | não | — | — |
| `failure_threshold` | `INTEGER` | não | — | — |
| `certificate_days` | `INTEGER` | não | — | — |
| `webhook_id` | `INTEGER` | sim | — | webhooks.id |
| `created_at` | `DATETIME` | não | — | — |

Unicidade adicional: `url_hash`.

Índices declarados no ORM: `ix_monitor_targets_host`, `ix_monitor_targets_kind`, `ix_monitor_targets_next_at`, `ix_monitor_targets_status`.

## `monitor_usage`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `scope` | `VARCHAR(260)` | não | sim | — |
| `window` | `VARCHAR(30)` | não | sim | — |
| `count` | `INTEGER` | não | — | — |

## `publications`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `VARCHAR(300)` | não | sim | — |
| `openalex_id` | `VARCHAR(200)` | não | — | — |
| `doi` | `VARCHAR(300)` | sim | — | — |
| `title` | `TEXT` | não | — | — |
| `year` | `INTEGER` | sim | — | — |
| `is_oa` | `BOOLEAN` | não | — | — |
| `citations` | `INTEGER` | não | — | — |
| `topics` | `JSON` | não | — | — |
| `authors` | `JSON` | não | — | — |
| `affiliations` | `JSON` | não | — | — |
| `openalex` | `JSON` | não | — | — |
| `crossref` | `JSON` | não | — | — |
| `fetched_at` | `DATETIME` | não | — | — |
| `crossref_at` | `DATETIME` | sim | — | — |
| `crossref_checked_at` | `DATETIME` | sim | — | — |

Unicidade adicional: `openalex_id`.

Índices declarados no ORM: `ix_publications_doi`.

## `record_reviews`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `active_key` | `VARCHAR(500)` | sim | — | — |
| `run_id` | `INTEGER` | não | — | runs.id |
| `source` | `VARCHAR(30)` | não | — | — |
| `entity_id` | `VARCHAR(400)` | não | — | — |
| `reason` | `TEXT` | não | — | — |
| `params` | `JSON` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `retry_run_id` | `INTEGER` | sim | — | runs.id |
| `created_at` | `DATETIME` | não | — | — |

Unicidade adicional: `active_key`.

Índices declarados no ORM: `ix_record_reviews_source`.

## `report_templates`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `owner_id` | `INTEGER` | não | — | users.id |
| `name` | `VARCHAR(100)` | não | — | — |
| `filters` | `JSON` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |

Índices declarados no ORM: `ix_report_templates_owner_id`.

## `reports`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `owner_id` | `INTEGER` | não | — | users.id |
| `template_id` | `INTEGER` | sim | — | report_templates.id |
| `dispatch_key` | `VARCHAR(200)` | sim | — | — |
| `name` | `VARCHAR(100)` | não | — | — |
| `filters` | `JSON` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `content` | `TEXT` | não | — | — |
| `rows` | `INTEGER` | não | — | — |
| `total` | `INTEGER` | não | — | — |
| `message` | `TEXT` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |
| `started_at` | `DATETIME` | sim | — | — |
| `finished_at` | `DATETIME` | sim | — | — |

Unicidade adicional: `dispatch_key`.

Índices declarados no ORM: `ix_reports_owner_id`.

## `researchers`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `orcid` | `VARCHAR(30)` | não | sim | — |
| `name` | `VARCHAR(500)` | não | — | — |
| `data` | `JSON` | não | — | — |
| `fetched_at` | `DATETIME` | não | — | — |

## `rules`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `name` | `VARCHAR(100)` | não | — | — |
| `kind` | `VARCHAR(30)` | não | — | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `threshold` | `INTEGER` | não | — | — |
| `topic` | `VARCHAR(150)` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |
| `webhook_id` | `INTEGER` | sim | — | webhooks.id |

## `run_checkpoints`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `run_id` | `INTEGER` | não | sim | runs.id |
| `key` | `VARCHAR(64)` | não | sim | — |
| `data` | `JSON` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

## `run_entities`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `run_id` | `INTEGER` | não | sim | runs.id |
| `kind` | `VARCHAR(30)` | não | sim | — |
| `entity_id` | `VARCHAR(400)` | não | sim | — |

## `run_log`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `run_id` | `INTEGER` | não | — | runs.id |
| `kind` | `VARCHAR(40)` | não | — | — |
| `message` | `TEXT` | não | — | — |
| `data` | `JSON` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

Índices declarados no ORM: `ix_run_log_run_id`.

## `run_runtime`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `run_id` | `INTEGER` | não | sim | runs.id |
| `dispatch_key` | `VARCHAR(200)` | sim | — | — |
| `requested` | `VARCHAR(20)` | não | — | — |
| `lease` | `VARCHAR(40)` | não | — | — |
| `stage` | `VARCHAR(30)` | não | — | — |
| `context` | `JSON` | não | — | — |
| `responses` | `INTEGER` | não | — | — |
| `pages` | `INTEGER` | não | — | — |
| `cache_bytes` | `INTEGER` | não | — | — |
| `retries` | `INTEGER` | não | — | — |
| `next_at` | `DATETIME` | sim | — | — |
| `heartbeat` | `DATETIME` | não | — | — |

Unicidade adicional: `dispatch_key`.

## `runs`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `active_key` | `VARCHAR(100)` | sim | — | — |
| `params` | `JSON` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |
| `started_at` | `DATETIME` | sim | — | — |
| `finished_at` | `DATETIME` | sim | — | — |
| `records` | `INTEGER` | não | — | — |
| `new` | `INTEGER` | não | — | — |
| `updated` | `INTEGER` | não | — | — |
| `rejected` | `INTEGER` | não | — | — |
| `duration_ms` | `INTEGER` | não | — | — |
| `attempts` | `INTEGER` | não | — | — |
| `http_calls` | `INTEGER` | não | — | — |
| `details` | `JSON` | não | — | — |
| `message` | `TEXT` | não | — | — |
| `error_code` | `VARCHAR(50)` | não | — | — |
| `actor` | `VARCHAR(100)` | não | — | — |

Unicidade adicional: `active_key`.

Índices declarados no ORM: `ix_runs_source`, `ix_runs_status`.

## `saved_matches`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `search_id` | `INTEGER` | não | sim | saved_searches.id |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |

## `saved_searches`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `user_id` | `INTEGER` | não | — | users.id |
| `name` | `VARCHAR(100)` | não | — | — |
| `filters` | `JSON` | não | — | — |
| `alerts_enabled` | `BOOLEAN` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

Índices declarados no ORM: `ix_saved_searches_user_id`.

## `schedules`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `source` | `VARCHAR(30)` | não | — | — |
| `interval_minutes` | `INTEGER` | não | — | — |
| `next_at` | `DATETIME` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |
| `params` | `JSON` | não | — | — |

## `search_alerts`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `user_id` | `INTEGER` | não | — | users.id |
| `search_id` | `INTEGER` | não | — | saved_searches.id |
| `publication_id` | `VARCHAR(300)` | não | — | publications.id |
| `read` | `BOOLEAN` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |

Unicidade adicional: `search_id, publication_id`.

Índices declarados no ORM: `ix_search_alerts_user_id`.

## `search_documents`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `kind` | `VARCHAR(30)` | não | sim | — |
| `entity_id` | `VARCHAR(400)` | não | sim | — |
| `title` | `TEXT` | não | — | — |
| `normalized_title` | `TEXT` | não | — | — |
| `body` | `TEXT` | não | — | — |
| `subtitle` | `TEXT` | não | — | — |
| `source` | `VARCHAR(50)` | não | — | — |
| `collected_at` | `DATETIME` | não | — | — |

Índices declarados no ORM: `ix_search_documents_normalized_title`.

## `search_identifiers`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `kind` | `VARCHAR(30)` | não | sim | — |
| `entity_id` | `VARCHAR(400)` | não | sim | — |
| `value` | `VARCHAR(500)` | não | sim | — |

Índices declarados no ORM: `ix_search_identifiers_value`.

## `sessions`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `token_hash` | `VARCHAR(64)` | não | sim | — |
| `user_id` | `INTEGER` | não | — | users.id |
| `expires_at` | `DATETIME` | não | — | — |

## `source_policies`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `source` | `VARCHAR(30)` | não | sim | — |
| `enabled` | `BOOLEAN` | não | — | — |
| `per_run` | `INTEGER` | não | — | — |
| `per_minute` | `INTEGER` | não | — | — |
| `per_day` | `INTEGER` | não | — | — |
| `cache_mb` | `INTEGER` | não | — | — |
| `auto_retries` | `INTEGER` | não | — | — |
| `overlap_days` | `INTEGER` | não | — | — |

## `source_usage`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `source` | `VARCHAR(30)` | não | sim | — |
| `window` | `VARCHAR(30)` | não | sim | — |
| `count` | `INTEGER` | não | — | — |

## `source_watermarks`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `scope` | `VARCHAR(250)` | não | sim | — |
| `date` | `VARCHAR(30)` | não | — | — |
| `updated_at` | `DATETIME` | não | — | — |

## `topics`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `VARCHAR(200)` | não | sim | — |
| `name` | `VARCHAR(500)` | não | — | — |
| `normalized_name` | `VARCHAR(500)` | não | — | — |

Índices declarados no ORM: `ix_topics_normalized_name`.

## `users`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `username` | `VARCHAR(80)` | não | — | — |
| `password_hash` | `TEXT` | não | — | — |
| `role` | `VARCHAR(20)` | não | — | — |
| `active` | `BOOLEAN` | não | — | — |

Unicidade adicional: `username`.

## `webhooks`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `name` | `VARCHAR(100)` | não | — | — |
| `url` | `TEXT` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |

## `work_affiliations`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |
| `institution_id` | `VARCHAR(200)` | não | sim | — |
| `name` | `VARCHAR(500)` | não | — | — |

## `work_authors`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |
| `author_id` | `VARCHAR(200)` | não | sim | authors.id |

## `work_institutions`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |
| `institution_id` | `VARCHAR(200)` | não | sim | institutions.id |

## `work_metadata`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |
| `language` | `VARCHAR(20)` | não | — | — |
| `work_type` | `VARCHAR(80)` | não | — | — |
| `journal` | `VARCHAR(500)` | não | — | — |
| `normalized_journal` | `VARCHAR(500)` | não | — | — |
| `normalized_abstract` | `TEXT` | não | — | — |
| `has_abstract` | `BOOLEAN` | não | — | — |
| `has_doi` | `BOOLEAN` | não | — | — |
| `is_retracted` | `BOOLEAN` | sim | — | — |

Índices declarados no ORM: `ix_work_metadata_has_abstract`, `ix_work_metadata_has_doi`, `ix_work_metadata_is_retracted`, `ix_work_metadata_language`, `ix_work_metadata_normalized_journal`, `ix_work_metadata_work_type`.

## `work_topics`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `publication_id` | `VARCHAR(300)` | não | sim | publications.id |
| `topic_id` | `VARCHAR(200)` | não | sim | topics.id |

## `workflow_runs`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `workflow_id` | `INTEGER` | não | — | workflows.id |
| `owner_id` | `INTEGER` | não | — | users.id |
| `dispatch_key` | `VARCHAR(200)` | sim | — | — |
| `active_key` | `VARCHAR(100)` | sim | — | — |
| `snapshot` | `JSON` | não | — | — |
| `status` | `VARCHAR(30)` | não | — | — |
| `step` | `INTEGER` | não | — | — |
| `child_id` | `INTEGER` | sim | — | runs.id |
| `report_id` | `INTEGER` | sim | — | — |
| `requested` | `VARCHAR(20)` | não | — | — |
| `history` | `JSON` | não | — | — |
| `message` | `TEXT` | não | — | — |
| `created_at` | `DATETIME` | não | — | — |
| `finished_at` | `DATETIME` | sim | — | — |

Unicidade adicional: `active_key`; `dispatch_key`.

## `workflows`

| Coluna | Tipo | Aceita nulo | PK | FK |
| --- | --- | --- | --- | --- |
| `id` | `INTEGER` | não | sim | — |
| `owner_id` | `INTEGER` | não | — | users.id |
| `name` | `VARCHAR(100)` | não | — | — |
| `steps` | `JSON` | não | — | — |
| `params` | `JSON` | não | — | — |
| `allow_partial` | `BOOLEAN` | não | — | — |
| `enabled` | `BOOLEAN` | não | — | — |

Índices específicos PostgreSQL (GIN/trigramas/expressões) também podem ser criados pelas migrações e não aparecem integralmente no metadata do ORM.
