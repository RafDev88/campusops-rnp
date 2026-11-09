import csv,io
from sqlalchemy import func,select,update
from sqlalchemy.exc import IntegrityError
from .database import Session
from .domain import User,utcnow
from . import orchestration_models as m
from .discovery import PublicationFilters,publication_query


def enqueue_report(owner_id,name,filters,template_id=None,dispatch_key=None):
    with Session() as db:
        if dispatch_key:
            existing=db.scalar(select(m.Report.id).where(m.Report.dispatch_key==dispatch_key))
            if existing:return existing
        item=m.Report(owner_id=owner_id,name=name,filters=PublicationFilters.model_validate(filters).model_dump(),template_id=template_id,dispatch_key=dispatch_key)
        db.add(item)
        try: db.commit()
        except IntegrityError:
            db.rollback()
            existing=db.scalar(select(m.Report.id).where(m.Report.dispatch_key==dispatch_key)) if dispatch_key else None
            if existing:return existing
            raise
        identifier=item.id
    from .tasks import generate_report
    try:generate_report.delay(identifier)
    except Exception:pass
    return identifier


def render_report(identifier):
    with Session() as db:
        claimed=db.execute(update(m.Report).where(m.Report.id==identifier,m.Report.status=='queued').values(status='running',started_at=utcnow()))
        db.commit()
        if not claimed.rowcount:return
        item=db.get(m.Report,identifier)
        owner=db.get(User,item.owner_id)
        filters=PublicationFilters.model_validate(item.filters)
        if not owner or not owner.active:
            item.status,item.message,item.finished_at='failed','Conta de destino desativada.',utcnow();db.commit();return
        owner_id=owner.id
    try:
        from .discovery_api import export_publications
        response=export_publications(filters=filters,user={'id':owner_id})
        content=response.body.decode('utf-8')
        rows=max(0,len(list(csv.reader(io.StringIO(content.lstrip('\ufeff')))))-1)
        with Session() as db:
            total=db.scalar(select(func.count()).select_from(publication_query(db,filters,owner_id).order_by(None).subquery()))
            item=db.get(m.Report,identifier)
            item.status,item.content,item.rows,item.total='ready',content,rows,total
            item.finished_at,item.message=utcnow(),'Arquivo gerado. '+('Exportação limitada a 10 mil resultados.' if total>rows else 'Todos os resultados foram incluídos.')
            db.commit()
    except Exception:
        with Session() as db:
            item=db.get(m.Report,identifier)
            item.status,item.message,item.finished_at='failed','Falha ao gerar relatório. Consulte os logs.',utcnow()
            db.commit()
        import structlog
        structlog.get_logger().exception('report_failed',report_id=identifier)
