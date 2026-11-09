from datetime import date,timedelta
from sqlalchemy import func,select
from .database import Session
from .domain import Profile,Publication,Researcher,WorkInstitution,utcnow
from .models import Institution
from . import orchestration_models as m
from .job_runtime import freeze,policy
from .providers import SourceError


async def collect(identifier,source,params,provider):
    profiles,items,details,rejects=[],[],{},[]
    if source=='ror':
        items,details=await provider.ror(params)
    elif source=='openalex':
        with Session() as db:
            if params.get('institution_id'):
                if not db.get(Institution,params['institution_id']): raise SourceError('selection','Instituição não cadastrada.')
                selected=[params['institution_id']]
            else: selected=list(db.scalars(select(Profile.institution_id).where(Profile.watched.is_(True))).all())
        if not selected: raise SourceError('selection','Selecione pelo menos uma instituição para acompanhar.')
        selected=freeze(identifier,'institutions',selected)
        if len(selected)>50: raise SourceError('selection','Limite de 50 instituições por coleta.')
        collected_on=freeze(identifier,'collection_date',utcnow().date().isoformat())
        scopes=[]
        for institution_id in selected:
            scope_key=f"openalex:{institution_id}:{params.get('year_from',2024)}:{params.get('since_date','')}"
            extra={k:params[k] for k in ('query','year_to','language','work_type') if params.get(k)}
            if extra:
                import hashlib,json
                scope_key+=':'+hashlib.sha256(json.dumps(extra,sort_keys=True).encode()).hexdigest()[:24]
            since=max(str(params.get('year_from',2024))+'-01-01',params.get('since_date') or '1900-01-01')
            with Session() as db:
                marker=db.get(m.Watermark,scope_key)
                if marker and params.get('incremental',True):
                    since=max(since,(date.fromisoformat(marker.date)-timedelta(days=policy(db,source).overlap_days)).isoformat())
            since=freeze(identifier,'since:'+institution_id,since)
            remote,works,scope=await provider.openalex(institution_id,{**params,'_since':since})
            scope={**scope,'since':since,'watermark_key':scope_key,'collected_on':collected_on,'incremental_field':'publication_date'}
            profiles.append((institution_id,remote));items.extend((institution_id,work) for work in works);scopes.append(scope)
        details={'coverage':scopes,'complete':all(s['complete'] for s in scopes),'year_from':params.get('year_from',2024),
                 'incremental':params.get('incremental',True),'scope':'Janela por data de publicação; revisões históricas exigem reconciliação completa.'}
    elif source=='crossref':
        with Session() as db:
            query=select(Publication.id,Publication.doi).where(Publication.doi.is_not(None))
            if params.get('institution_id'):
                query=query.join(WorkInstitution).where(WorkInstitution.institution_id==params['institution_id'])
            if params.get('publication_ids'): query=query.where(Publication.id.in_(params['publication_ids']))
            if params.get('from_run_id'):
                query=query.where(Publication.id.in_(select(m.RunEntity.entity_id).where(m.RunEntity.run_id==params['from_run_id'],m.RunEntity.kind=='publication')))
            if params.get('only_pending'): query=query.where(Publication.crossref_checked_at.is_(None))
            total=db.scalar(select(func.count()).select_from(query.subquery()))
            selected=[list(r) for r in db.execute(query.order_by(Publication.crossref_checked_at.asc().nullsfirst(),Publication.id).limit(params.get('limit',25)))]
        selected=freeze(identifier,'crossref_selection',selected)
        if not selected and not params.get('_workflow'): raise SourceError('selection','Nenhuma publicação com DOI disponível para enriquecer.')
        for work_id,doi in selected:
            try: items.append((work_id,await provider.crossref(doi)))
            except SourceError as exc:
                if exc.code!='not_found': raise
                rejects.append({'publication_id':work_id,'reason':'DOI não encontrado no Crossref.'})
        details={'selected':len(selected),'available_with_doi':total,'rejections':rejects,'complete':len(selected)>=total,
                 'scope':'Enriquecimento por DOI no escopo selecionado.'}
    elif source=='orcid':
        if params.get('orcid'): identifiers=[params['orcid']]
        elif params.get('auto_discover'):
            with Session() as db:
                query=select(Publication)
                if params.get('from_run_id'):
                    query=query.where(Publication.id.in_(select(m.RunEntity.entity_id).where(m.RunEntity.run_id==params['from_run_id'],m.RunEntity.kind=='publication')))
                elif params.get('institution_id'):
                    query=query.join(WorkInstitution).where(WorkInstitution.institution_id==params['institution_id'])
                from .metadata import effective_authors
                identifiers=sorted({a['orcid'].rsplit('/',1)[-1] for work in db.scalars(query) for a in effective_authors(work) if a.get('orcid')})
                identifiers=[i for i in identifiers if not db.get(Researcher,i)][:params.get('orcid_limit',5)]
        else: raise SourceError('selection','Informe o ORCID do pesquisador.')
        identifiers=freeze(identifier,'orcid_selection',identifiers)
        for orcid in identifiers:
            try: items.append(await provider.orcid(orcid))
            except SourceError as exc:
                if exc.code!='not_found': raise
                rejects.append({'orcid':orcid,'reason':'Perfil público não encontrado.'})
        details={'complete':not rejects,'selected':len(identifiers),'rejections':rejects,'scope':'Somente registros públicos dos identificadores selecionados.'}
    elif source=='ufrn':
        items,details=await provider.ufrn(params)
    else: raise SourceError('source','Fonte desconhecida.')
    return profiles,items,details,rejects
