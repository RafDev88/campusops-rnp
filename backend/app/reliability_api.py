"""Bounded SQL summaries: freshness is not a promise of complete provider coverage."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from .automation import aware
from .contracts import AutomationOverview, CatalogStatus
from .database import Session
from .domain import Publication, Run, Schedule
from .orchestration_models import CalendarSchedule, Report, Runtime, WorkflowRun
from .monitor_models import MonitorTarget
from .security import current_user

router = APIRouter()


@router.get('/catalog-status', response_model=CatalogStatus)
def catalog_status(user=Depends(current_user)):
    with Session() as db:
        sources = []
        for source in ('ror', 'openalex', 'crossref', 'orcid', 'ufrn'):
            latest = db.scalar(select(Run).where(Run.source == source).order_by(Run.id.desc()).limit(1))
            collected = db.scalar(select(func.max(Run.finished_at)).where(
                Run.source == source, Run.status.in_(('success', 'partial'))))
            complete = latest.details.get('complete') if latest else None
            coverage = ('partial' if latest and latest.status == 'partial' or complete is False else
                        'complete' if latest and latest.status == 'success' and complete is True else 'unknown')
            sources.append(dict(source=source, status=latest.status if latest else 'not_collected',
                                checked_at=latest.finished_at if latest else None, collected_at=collected,
                                coverage=coverage, message=latest.message if latest else 'Nenhuma coleta registrada.'))
        return dict(total_publications=db.scalar(select(func.count()).select_from(Publication)), sources=sources,
                    scope='Situação das coletas registradas. Cobertura completa refere-se somente ao escopo da execução, não a toda a fonte ou à pesquisa filtrada.')


def recommendation(status, code=''):
    if status == 'paused':
        return 'Revise o motivo da pausa e os limites antes de retomar.'
    if status == 'failed':
        return {'credentials': 'Confira a credencial da fonte antes de reprocessar.',
                'schema_change': 'Revise o contrato do adaptador antes de refazer respostas.',
                'tls_certificate': 'Confira a cadeia HTTPS sem desativar a validação.'}.get(code, 'Abra os detalhes e revise a causa antes de reprocessar.')
    if status == 'partial':
        return 'Confira cobertura e rejeições antes de ampliar a coleta.'
    return 'Acompanhe a etapa atual; mensagens na fila ainda não significam conclusão.'


@router.get('/automation-overview', response_model=AutomationOverview)
def automation_overview(user=Depends(current_user)):
    with Session() as db:
        active = Run.status.in_(('queued', 'running', 'paused'))
        runs = db.execute(select(Run, Runtime).outerjoin(Runtime, Runtime.run_id == Run.id).where(
            Run.status.in_(('queued', 'running', 'paused', 'failed', 'partial'))).order_by(
            active.desc(), Run.id.desc()).limit(12)).all()
        items = [dict(id=f'run:{run.id}', kind='coleta', title=run.source.upper(), status=run.status,
                      stage=state.stage if state else '', next_at=state.next_at if state else None,
                      message=run.message, action=recommendation(run.status, run.error_code), route='runs', resource_id=run.id)
                 for run, state in runs]
        # Shared source/workflow calendars and only this account's report calendars.
        calendars = db.scalars(select(CalendarSchedule).where(CalendarSchedule.enabled.is_(True),
            (CalendarSchedule.target != 'report') | (CalendarSchedule.owner_id == user['id'])).order_by(CalendarSchedule.next_at).limit(8))
        for item in calendars:
            items.append(dict(id=f'calendar:{item.id}', kind='agenda', title=item.name, status='scheduled',
                              next_at=item.next_at, action='Confira horário, fuso e destino na agenda.', route='automation'))
        for item in db.scalars(select(Schedule).where(Schedule.enabled.is_(True)).order_by(Schedule.next_at).limit(8)):
            items.append(dict(id=f'schedule:{item.id}', kind='agenda', title=item.source.upper(), status='scheduled',
                              next_at=item.next_at, action='Agenda por intervalo; evite duplicar um calendário equivalente.', route='automation'))
        for item in db.scalars(select(WorkflowRun).where(WorkflowRun.status.in_(('running','waiting','paused','failed'))).order_by(WorkflowRun.id.desc()).limit(6)):
            # Snapshot may contain private report configuration: never serialize it here.
            items.append(dict(id=f'flow:{item.id}', kind='fluxo', title=f'Fluxo #{item.id}', status=item.status,
                              stage=f'Etapa {item.step + 1}', message=item.message,
                              action='Abra o fluxo para acompanhar suas etapas.', route='flows'))
        for item in db.scalars(select(Report).where(Report.owner_id == user['id'], Report.status.in_(('queued','running','failed'))).order_by(Report.id.desc()).limit(6)):
            items.append(dict(id=f'report:{item.id}', kind='relatório', title=item.name, status=item.status,
                              message=item.message, action='Confira o relatório privado da sua conta.', route='reports'))
        for item in db.scalars(select(MonitorTarget).where(MonitorTarget.status.not_in(('available','not_checked')),
                MonitorTarget.archived.is_(False)).order_by(MonitorTarget.checked_at.desc()).limit(6)):
            items.append(dict(id=f'monitor:{item.id}', kind='link', title=item.name, status=item.status,
                              next_at=item.next_at, action='Confira o diagnóstico HTTP/HTTPS e o histórico antes de alterar o endereço.', route='monitoring'))
        enabled = db.scalar(select(func.count()).select_from(CalendarSchedule).where(CalendarSchedule.enabled.is_(True),
            (CalendarSchedule.target != 'report') | (CalendarSchedule.owner_id == user['id'])))
        enabled += db.scalar(select(func.count()).select_from(Schedule).where(Schedule.enabled.is_(True)))
        return dict(active_runs=db.scalar(select(func.count()).select_from(Run).where(active)),
                    failed_runs=db.scalar(select(func.count()).select_from(Run).where(Run.status == 'failed')),
                    enabled_schedules=enabled, items=items,
                    scope='Resumo limitado das coletas, fluxos e agendas compartilhados e relatórios da sua conta. Falhas incluem histórico; consulte detalhes antes de agir.')
