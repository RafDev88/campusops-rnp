"""Discover unique public links without making network requests."""
from datetime import timedelta
from sqlalchemy import select
from .database import Session
from .domain import Dataset,Profile,Publication,utcnow
from .models import Institution
from .metadata import bibliographic
from . import monitor_models as m
from .monitor_network import API_ENDPOINTS,normalize_url,url_key


def config(db):
    item=db.get(m.MonitorConfig,1)
    if not item:item=m.MonitorConfig(id=1);db.add(item);db.flush()
    return item


def sync_inventory(actor='scheduler'):
    from .domain import Audit
    with Session() as db:
        # Serializes discovery, including manual discovery and scheduler discovery.
        config(db)
        db.scalar(select(m.MonitorConfig).where(m.MonitorConfig.id==1).with_for_update())
        existing={r.url_hash:r for r in db.scalars(select(m.MonitorTarget))}
        refs={(r.target_id,r.kind,r.entity_id,r.role):r for r in db.scalars(select(m.MonitorReference))}
        wanted=set();expected={};created=skipped=0
        def add(url,name,kind,source='',reference=None,expected_type=''):
            nonlocal created,skipped
            if not url:return
            try:url=normalize_url(url)
            except ValueError:skipped+=1;return
            key=url_key(url);target=existing.get(key)
            if not target:
                from urllib.parse import urlsplit
                minutes=15 if kind=='api' else 1440
                # Spread catalogue checks across the day, rather than starting a burst.
                stagger=(int(key[:8],16)%(minutes*60)) if kind!='api' else 60
                target=m.MonitorTarget(url_hash=key,url=url,host=urlsplit(url).hostname,name=name[:300],kind=kind,source=source,managed=True,
                    interval_minutes=minutes,next_at=utcnow()+timedelta(seconds=stagger))
                db.add(target);db.flush();existing[key]=target;created+=1
            if expected_type:expected[target.id]=expected_type
            if reference:
                refkind,entity,role,title=reference
                refkey=(target.id,refkind,entity,role)
                wanted.add(refkey)
                row=refs.get(refkey)
                if not row:
                    row=m.MonitorReference(target_id=target.id,kind=refkind,entity_id=entity,role=role,title=title[:500]);db.add(row);refs[refkey]=row
                row.title=title[:500]
                if target.archived:target.archived=False
        for source,(name,url) in API_ENDPOINTS.items():add(url,name+' · endpoint de referência','api',source)
        for work in db.scalars(select(Publication)):
            meta=bibliographic(work)
            for role,url in [('doi','https://doi.org/'+work.doi if work.doi else ''),('page',meta['landing_url']),('pdf',meta['pdf_url'])]:
                add(url,work.title,'publication',reference=('publication',work.id,role,work.title),expected_type='pdf' if role=='pdf' else '')
        for dataset in db.scalars(select(Dataset)):
            add(dataset.url,dataset.title,'dataset',reference=('dataset',dataset.id,'page',dataset.title))
            for resource in dataset.resources or []:
                format=str(resource.get('format') or '').lower()
                add(resource.get('url'),resource.get('name') or dataset.title,'file',reference=('dataset',dataset.id,('resource:'+str(resource.get('id') or url_key(resource.get('url') or '')))[:100],dataset.title),expected_type=format if format in {'pdf','csv','json','xml','zip'} else '')
        for profile in db.scalars(select(Profile).where(Profile.watched.is_(True))):
            institution=db.get(Institution,profile.institution_id)
            if not institution:continue
            for link in ((profile.data or {}).get('ror') or {}).get('links',[]):
                if isinstance(link,dict) and link.get('type')=='website':
                    add(link.get('value'),institution.name,'portal',reference=('institution',institution.id,'website',institution.name))
        for key,row in refs.items():
            if key not in wanted:db.delete(row)
        current_ids={key[0] for key in wanted}
        for target in existing.values():
            if target.managed:target.expected_type=expected.get(target.id,'')
            if target.managed and target.kind!='api' and target.id not in current_ids:
                target.archived,target.enabled=True,False
        config(db).next_discovery=utcnow()+timedelta(hours=1)
        if actor!='scheduler':db.add(Audit(actor=actor,action='monitor.discovery',detail={'created':created,'skipped':skipped,'references':len(wanted)}))
        db.commit()
        return {'created':created,'skipped':skipped,'references':len(wanted),'targets':len(existing)}
