# Referência gerada do backend

Gerado por `scripts/document-backend.py`. Não editar as tabelas manualmente.

O gerador importa o aplicativo sem executar seu lifespan: não aplica migrações, não conecta ao banco e não inicia tarefas. O OpenAPI é a referência de parâmetros e validações. Permissões abaixo são o mínimo da dependência; propriedade e regras específicas também são verificadas dentro dos handlers.

## Operações HTTP

| Método | Caminho | Perfil mínimo | Módulo / função |
| --- | --- | --- | --- |
| POST | `/api/account/password` | consulta | `app.account_api.change_password` |
| GET | `/api/account/sessions` | consulta | `app.account_api.sessions` |
| DELETE | `/api/account/sessions/{identifier}` | consulta | `app.account_api.revoke` |
| GET | `/api/audit` | administrador | `app.read_api.audit_log` |
| POST | `/api/auth/login` | público | `app.main.sign_in` |
| POST | `/api/auth/logout` | consulta | `app.main.logout` |
| GET | `/api/auth/me` | consulta | `app.main.me` |
| POST | `/api/auth/setup` | público | `app.main.setup` |
| GET | `/api/auth/status` | público | `app.main.auth_status` |
| GET | `/api/automation-overview` | consulta | `app.reliability_api.automation_overview` |
| POST | `/api/calendar-preview` | consulta | `app.orchestration_api.calendar_preview` |
| GET | `/api/calendar-schedules` | consulta | `app.orchestration_api.calendars` |
| POST | `/api/calendar-schedules` | consulta | `app.orchestration_api.add_calendar` |
| PATCH | `/api/calendar-schedules/{identifier}` | consulta | `app.orchestration_api.toggle_calendar` |
| GET | `/api/catalog-coverage` | consulta | `app.catalog_api.coverage` |
| GET | `/api/catalog-status` | consulta | `app.reliability_api.catalog_status` |
| GET | `/api/dashboard` | consulta | `app.read_api.dashboard` |
| GET | `/api/data-changes` | consulta | `app.orchestration_api.changes` |
| GET | `/api/dataset` | consulta | `app.discovery_api.dataset` |
| GET | `/api/datasets` | consulta | `app.read_api.datasets` |
| GET | `/api/digest` | consulta | `app.read_api.digest` |
| GET | `/api/events` | consulta | `app.read_api.events` |
| GET | `/api/exports/publications.csv` | consulta | `app.discovery_api.export_publications` |
| POST | `/api/favorites` | consulta | `app.discovery_api.favorite` |
| GET | `/api/health` | público | `app.main.health` |
| GET | `/api/incidents` | consulta | `app.read_api.incidents` |
| POST | `/api/incidents/{identifier}/resolve` | operador | `app.write_api.resolve_incident` |
| GET | `/api/institution-facets` | consulta | `app.catalog_api.institution_facets` |
| GET | `/api/institution-profile` | consulta | `app.read_api.institution_profile` |
| GET | `/api/institutions` | consulta | `app.read_api.institutions` |
| GET | `/api/legacy-executions` | consulta | `app.read_api.legacy_executions` |
| GET | `/api/metrics` | administrador | `app.read_api.metrics` |
| GET | `/api/monitor-settings` | consulta | `app.monitor_api.settings` |
| PUT | `/api/monitor-settings` | administrador | `app.monitor_api.save_settings` |
| GET | `/api/monitors` | consulta | `app.monitor_api.targets` |
| POST | `/api/monitors` | operador | `app.monitor_api.create` |
| POST | `/api/monitors/check-apis` | operador | `app.monitor_api.check_apis` |
| POST | `/api/monitors/discover` | operador | `app.monitor_api.discover` |
| GET | `/api/monitors/{identifier}` | consulta | `app.monitor_api.detail` |
| PATCH | `/api/monitors/{identifier}` | operador | `app.monitor_api.update_target` |
| POST | `/api/monitors/{identifier}/check` | operador | `app.monitor_api.check_now` |
| GET | `/api/publication` | consulta | `app.discovery_api.publication` |
| GET | `/api/publication-facets` | consulta | `app.discovery_api.facets` |
| GET | `/api/publications` | consulta | `app.discovery_api.publications` |
| GET | `/api/quality` | consulta | `app.read_api.quality` |
| GET | `/api/record-reviews` | consulta | `app.orchestration_api.reviews` |
| POST | `/api/record-reviews/{identifier}/ignore` | operador | `app.orchestration_api.ignore_review` |
| POST | `/api/record-reviews/{identifier}/retry` | operador | `app.orchestration_api.retry_review` |
| GET | `/api/report-templates` | consulta | `app.orchestration_api.report_templates` |
| POST | `/api/report-templates` | consulta | `app.orchestration_api.add_report_template` |
| POST | `/api/report-templates/{identifier}/generate` | consulta | `app.orchestration_api.generate` |
| GET | `/api/reports` | consulta | `app.orchestration_api.reports` |
| GET | `/api/reports/{identifier}/download` | consulta | `app.orchestration_api.download_report` |
| GET | `/api/researcher-profile` | consulta | `app.discovery_api.researcher_profile` |
| GET | `/api/researchers` | consulta | `app.read_api.researchers` |
| GET | `/api/rules` | consulta | `app.read_api.rules` |
| POST | `/api/rules` | operador | `app.write_api.add_rule` |
| POST | `/api/rules/preview` | operador | `app.orchestration_api.rule_preview` |
| GET | `/api/runs` | consulta | `app.read_api.runs` |
| POST | `/api/runs/{identifier}/control` | operador | `app.orchestration_api.run_control` |
| POST | `/api/runs/{identifier}/retry` | operador | `app.write_api.retry` |
| GET | `/api/runs/{identifier}/runtime` | consulta | `app.orchestration_api.progress` |
| GET | `/api/saved-searches` | consulta | `app.discovery_api.saved_searches` |
| POST | `/api/saved-searches` | consulta | `app.discovery_api.save_search` |
| DELETE | `/api/saved-searches/{identifier}` | consulta | `app.discovery_api.remove_saved_search` |
| GET | `/api/schedules` | consulta | `app.read_api.schedules` |
| POST | `/api/schedules` | operador | `app.write_api.add_schedule` |
| GET | `/api/search` | consulta | `app.discovery_api.search` |
| GET | `/api/search-alerts` | consulta | `app.discovery_api.search_alerts` |
| POST | `/api/search-alerts/{identifier}/read` | consulta | `app.discovery_api.read_alert` |
| GET | `/api/search/suggestions` | consulta | `app.discovery_api.suggestions` |
| GET | `/api/source-policies` | consulta | `app.orchestration_api.policies` |
| PUT | `/api/source-policies/{source}` | administrador | `app.orchestration_api.update_policy` |
| GET | `/api/sources` | consulta | `app.read_api.sources` |
| POST | `/api/sync` | operador | `app.write_api.sync` |
| GET | `/api/users` | administrador | `app.main.users` |
| POST | `/api/users` | administrador | `app.main.create_user` |
| PATCH | `/api/users/{identifier}` | administrador | `app.main.toggle_user` |
| POST | `/api/watch` | operador | `app.write_api.watch` |
| GET | `/api/webhooks` | administrador | `app.read_api.webhooks` |
| POST | `/api/webhooks` | administrador | `app.write_api.add_webhook` |
| POST | `/api/workflow-runs/{identifier}/control` | operador | `app.orchestration_api.control_flow` |
| GET | `/api/workflows` | consulta | `app.orchestration_api.workflows` |
| POST | `/api/workflows` | operador | `app.orchestration_api.add_workflow` |
| PATCH | `/api/workflows/{identifier}` | operador | `app.orchestration_api.enable_workflow` |
| POST | `/api/workflows/{identifier}/start` | operador | `app.orchestration_api.launch` |
| PATCH | `/api/{collection}/{identifier}/enabled` | operador | `app.write_api.toggle_configuration` |

Total: **87 operações**. Escritas exigem `X-CampusOps: 1`, inclusive setup/login e comandos de consulta via POST.

## Tabelas e classes persistidas

Inventário dos modelos declarativos, incluindo o histórico legado. Colunas, índices e constraints estão nos modelos e nas migrações Alembic.

| Tabela | Classe | Arquivo |
| --- | --- | --- |
| `work_metadata` | `WorkMetadata` | `app/discovery_models.py` |
| `search_identifiers` | `SearchIdentifier` | `app/discovery_models.py` |
| `institution_fields` | `InstitutionField` | `app/discovery_models.py` |
| `search_documents` | `SearchDocument` | `app/discovery_models.py` |
| `topics` | `Topic` | `app/discovery_models.py` |
| `work_topics` | `WorkTopic` | `app/discovery_models.py` |
| `authors` | `Author` | `app/discovery_models.py` |
| `work_authors` | `WorkAuthor` | `app/discovery_models.py` |
| `work_affiliations` | `WorkAffiliation` | `app/discovery_models.py` |
| `favorites` | `Favorite` | `app/discovery_models.py` |
| `saved_searches` | `SavedSearch` | `app/discovery_models.py` |
| `saved_matches` | `SavedMatch` | `app/discovery_models.py` |
| `search_alerts` | `SearchAlert` | `app/discovery_models.py` |
| `users` | `User` | `app/domain.py` |
| `login_limits` | `LoginLimit` | `app/domain.py` |
| `sessions` | `SessionToken` | `app/domain.py` |
| `institution_profiles` | `Profile` | `app/domain.py` |
| `publications` | `Publication` | `app/domain.py` |
| `work_institutions` | `WorkInstitution` | `app/domain.py` |
| `researchers` | `Researcher` | `app/domain.py` |
| `datasets` | `Dataset` | `app/domain.py` |
| `runs` | `Run` | `app/domain.py` |
| `schedules` | `Schedule` | `app/domain.py` |
| `webhooks` | `Webhook` | `app/domain.py` |
| `rules` | `Rule` | `app/domain.py` |
| `incidents` | `Incident` | `app/domain.py` |
| `events` | `Event` | `app/domain.py` |
| `deliveries` | `Delivery` | `app/domain.py` |
| `audit` | `Audit` | `app/domain.py` |
| `institutions` | `Institution` | `app/models.py` |
| `executions` | `Execution` | `app/models.py` |
| `monitor_config` | `MonitorConfig` | `app/monitor_models.py` |
| `monitor_targets` | `MonitorTarget` | `app/monitor_models.py` |
| `monitor_references` | `MonitorReference` | `app/monitor_models.py` |
| `monitor_checks` | `MonitorCheck` | `app/monitor_models.py` |
| `monitor_usage` | `MonitorUsage` | `app/monitor_models.py` |
| `source_policies` | `SourcePolicy` | `app/orchestration_models.py` |
| `source_usage` | `Usage` | `app/orchestration_models.py` |
| `run_runtime` | `Runtime` | `app/orchestration_models.py` |
| `run_checkpoints` | `Checkpoint` | `app/orchestration_models.py` |
| `run_log` | `RunLog` | `app/orchestration_models.py` |
| `run_entities` | `RunEntity` | `app/orchestration_models.py` |
| `source_watermarks` | `Watermark` | `app/orchestration_models.py` |
| `record_reviews` | `Review` | `app/orchestration_models.py` |
| `data_changes` | `Change` | `app/orchestration_models.py` |
| `workflows` | `Workflow` | `app/orchestration_models.py` |
| `workflow_runs` | `WorkflowRun` | `app/orchestration_models.py` |
| `report_templates` | `ReportTemplate` | `app/orchestration_models.py` |
| `reports` | `Report` | `app/orchestration_models.py` |
| `calendar_schedules` | `CalendarSchedule` | `app/orchestration_models.py` |
| `calendar_fires` | `CalendarFire` | `app/orchestration_models.py` |

## Filtros de publicações

Defaults e limites vêm de `PublicationFilters`; os booleanos opcionais distinguem ausência, `true` e `false`.

| Parâmetro | Padrão | Schema |
| --- | --- | --- |
| `q` | `""` | `{"type": "string", "maxLength": 150, "default": "", "title": "Q"}` |
| `institution_id` | `""` | `{"type": "string", "maxLength": 200, "default": "", "title": "Institution Id"}` |
| `topic` | `""` | `{"type": "string", "maxLength": 200, "default": "", "title": "Topic"}` |
| `author` | `""` | `{"type": "string", "maxLength": 150, "default": "", "title": "Author"}` |
| `author_id` | `""` | `{"type": "string", "maxLength": 200, "default": "", "title": "Author Id"}` |
| `year` | `null` | `{"anyOf": [{"type": "integer", "maximum": 2100, "minimum": 1900}, {"type": "null"}], "title": "Year"}` |
| `year_from` | `null` | `{"anyOf": [{"type": "integer", "maximum": 2100, "minimum": 1900}, {"type": "null"}], "title": "Year From"}` |
| `year_to` | `null` | `{"anyOf": [{"type": "integer", "maximum": 2100, "minimum": 1900}, {"type": "null"}], "title": "Year To"}` |
| `oa` | `null` | `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "title": "Oa"}` |
| `source` | `""` | `{"enum": ["", "openalex", "crossref"], "type": "string", "default": "", "title": "Source"}` |
| `favorites` | `false` | `{"type": "boolean", "default": false, "title": "Favorites"}` |
| `mode` | `"all"` | `{"enum": ["all", "any", "phrase", "exact"], "type": "string", "default": "all", "title": "Mode"}` |
| `approximate` | `false` | `{"type": "boolean", "default": false, "title": "Approximate"}` |
| `search_in` | `"all"` | `{"enum": ["all", "title", "abstract"], "type": "string", "default": "all", "title": "Search In"}` |
| `language` | `""` | `{"type": "string", "maxLength": 20, "default": "", "title": "Language"}` |
| `work_type` | `""` | `{"type": "string", "maxLength": 80, "default": "", "title": "Work Type"}` |
| `journal` | `""` | `{"type": "string", "maxLength": 200, "default": "", "title": "Journal"}` |
| `has_abstract` | `null` | `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "title": "Has Abstract"}` |
| `has_doi` | `null` | `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "title": "Has Doi"}` |
| `retracted` | `null` | `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "title": "Retracted"}` |
| `citations_min` | `null` | `{"anyOf": [{"type": "integer", "maximum": 100000000, "minimum": 0}, {"type": "null"}], "title": "Citations Min"}` |
| `sort` | `"relevance"` | `{"enum": ["relevance", "recent", "title", "citations"], "type": "string", "default": "relevance", "title": "Sort"}` |
| `offset` | `0` | `{"type": "integer", "minimum": 0, "default": 0, "title": "Offset"}` |
| `limit` | `25` | `{"type": "integer", "maximum": 100, "minimum": 1, "default": 25, "title": "Limit"}` |
