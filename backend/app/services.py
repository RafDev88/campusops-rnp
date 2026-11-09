from time import perf_counter

import httpx
import structlog

from .database import Session
from .models import Execution, Institution

logger = structlog.get_logger()


async def synchronize(connector):
    start = perf_counter()
    with Session() as db:
        execution = Execution(status='running')
        db.add(execution)
        db.commit()
        execution_id = execution.id
    try:
        records = await connector.fetch()
        with Session() as db:
            for record in records:
                db.merge(Institution(**record))
            execution = db.get(Execution, execution_id)
            execution.status = 'success'
            execution.records = len(records)
            execution.duration_ms = int((perf_counter() - start) * 1000)
            execution.message = 'Primeira página do catálogo brasileiro sincronizada.'
            db.commit()
        logger.info('sync_completed', execution_id=execution_id, records=len(records))
    except (httpx.HTTPError, KeyError, ValueError, IndexError, TypeError) as exc:
        with Session() as db:
            execution = db.get(Execution, execution_id)
            execution.status = 'failed'
            execution.duration_ms = int((perf_counter() - start) * 1000)
            execution.message = 'Falha ao consultar ou validar a fonte ROR. Tente novamente.'
            db.commit()
        logger.warning('sync_failed', execution_id=execution_id, error_type=type(exc).__name__)
    return execution_id
