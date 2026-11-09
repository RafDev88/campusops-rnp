from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Source = Literal['ror', 'openalex', 'crossref', 'orcid', 'ufrn']


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=10, max_length=128)


class UserCreate(Credentials):
    role: Literal['admin', 'operator', 'viewer'] = 'viewer'


class SyncRequest(BaseModel):
    source: Source = 'ror'
    max_pages: int = Field(default=500, ge=1, le=500)
    year_from: int = Field(default=2024, ge=1900, le=2100)
    year_to: int | None=Field(default=None,ge=1900,le=2100)
    language: str=Field(default='',pattern=r'^([a-z]{2,3})?$')
    work_type: str=Field(default='',pattern=r'^[a-z-]{0,50}$')
    limit: int = Field(default=25, ge=1, le=200)
    orcid: str = Field(default='', max_length=30)
    institution_id: str = Field(default='', max_length=200)
    query: str = Field(default='', max_length=150)
    incremental: bool = True
    since_date: str = Field(default='',max_length=10)
    only_pending: bool = False
    auto_discover: bool = False
    orcid_limit: int = Field(default=5,ge=1,le=25)
    publication_ids: list[str] = Field(default_factory=list,max_length=200)
    from_run_id: int | None = Field(default=None,ge=1)

    @model_validator(mode='after')
    def validate_period(self):
        if self.year_to and self.year_to<self.year_from:raise ValueError('Ano final anterior ao inicial.')
        return self

    @field_validator('since_date')
    @classmethod
    def valid_date(cls,value):
        if value:
            from datetime import date
            date.fromisoformat(value)
        return value

    @field_validator('orcid')
    @classmethod
    def validate_orcid(cls, value):
        import re
        if value and not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', value):
            raise ValueError('Informe um ORCID no formato 0000-0000-0000-000X.')
        return value


class ScheduleCreate(BaseModel):
    source: Source
    interval_minutes: int = Field(ge=15, le=525600)
    params: SyncRequest

    @field_validator('params')
    @classmethod
    def bounded(cls, value):
        return value


class RuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    kind: Literal['failure_streak', 'new_publication', 'schema_change', 'dataset_changed', 'stale_source', 'weekly_digest']
    source: Literal['all', 'ror', 'openalex', 'crossref', 'orcid', 'ufrn'] = 'all'
    threshold: int = Field(default=3, ge=1, le=10080)
    topic: str = Field(default='', max_length=150)
    webhook_id: int | None = None


class WebhookCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    url: str = Field(max_length=2000)


class Toggle(BaseModel):
    enabled: bool


class Watch(BaseModel):
    institution_id: str = Field(max_length=200)
    watched: bool


class PolicyUpdate(BaseModel):
    enabled: bool=True
    per_run: int=Field(default=500,ge=1,le=5000)
    per_minute: int=Field(default=60,ge=1,le=600)
    per_day: int=Field(default=2000,ge=1,le=100000)
    cache_mb: int=Field(default=100,ge=1,le=500)
    auto_retries: int=Field(default=2,ge=0,le=5)
    overlap_days: int=Field(default=2,ge=0,le=30)


class RunControl(BaseModel):
    action: Literal['pause','cancel','resume']
    reset_checkpoint: bool=False


class WorkflowCreate(BaseModel):
    name: str=Field(min_length=3,max_length=100)
    steps: list[Literal['ror','openalex','crossref','orcid','ufrn','report']]=Field(min_length=1,max_length=6)
    params: SyncRequest=Field(default_factory=lambda:SyncRequest(source='openalex',max_pages=1,limit=25))
    allow_partial: bool=True

    @model_validator(mode='after')
    def valid_steps(self):
        if len(self.steps)!=len(set(self.steps)):raise ValueError('Uma etapa não pode ser repetida.')
        if 'report' in self.steps and self.steps[-1]!='report':raise ValueError('O relatório deve ser a última etapa.')
        return self


class CalendarCreate(BaseModel):
    name: str=Field(min_length=3,max_length=100)
    target: Literal['source','workflow','report']
    target_id: int | None=Field(default=None,ge=1)
    source: str=Field(default='',pattern=r'^(ror|openalex|crossref|orcid|ufrn)?$')
    params: SyncRequest=Field(default_factory=SyncRequest)
    cron: str=Field(min_length=9,max_length=100)
    timezone: str=Field(default='America/Sao_Paulo',max_length=100)
