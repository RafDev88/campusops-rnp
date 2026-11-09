import asyncio
import os

from celery import Celery

celery = Celery('campusops', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
celery.conf.update(
    task_serializer='json', accept_content=['json'], timezone='UTC', enable_utc=True,
    task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True, broker_connection_timeout=3,
    task_publish_retry=False, broker_transport_options={'visibility_timeout': 7500, 'socket_connect_timeout': 3},
    task_routes={'campusops.execute':{'queue':'ingestion'},'campusops.tick':{'queue':'control'},
                 'campusops.report':{'queue':'reports'},'campusops.webhook':{'queue':'notifications'},
                 'campusops.monitor':{'queue':'monitoring'}},
    beat_schedule={'operations-tick': {'task': 'campusops.tick', 'schedule': 60.0}},
)


@celery.task(name='campusops.execute', soft_time_limit=7000, time_limit=7100)
def execute_run(identifier):
    from .operations import perform
    asyncio.run(perform(identifier))
    from .orchestration import advance_workflows
    advance_workflows()
    advance_workflows()


@celery.task(name='campusops.tick')
def operations_tick():
    from .operations import tick
    from .automation_tick import automation_tick
    try:tick()
    finally:
        try:automation_tick()
        finally:
            from .monitor_service import monitor_tick
            monitor_tick()


@celery.task(name='campusops.report',soft_time_limit=300,time_limit=360)
def generate_report(identifier):
    from .reports import render_report
    render_report(identifier)
    from .orchestration import advance_workflows
    advance_workflows()
    advance_workflows()


@celery.task(name='campusops.webhook',soft_time_limit=60,time_limit=90)
def deliver_webhook(identifier):
    from .automation import deliver_pending
    deliver_pending(identifier)


@celery.task(name='campusops.monitor',soft_time_limit=70,time_limit=90)
def monitor_check(identifier):
    from .monitor_service import perform_check
    perform_check(identifier)
