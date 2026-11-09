from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from .database import Session
from .security import current_user
from .domain import Publication
from . import discovery_models as s

router=APIRouter()

@router.get('/institution-facets')
def institution_facets(user=Depends(current_user)):
    with Session() as db:
        result={}
        for field in ('country','region','city','type','status'):
            rows=db.execute(select(s.InstitutionField.value,func.min(s.InstitutionField.label),func.count()).where(s.InstitutionField.field==field).group_by(s.InstitutionField.value).order_by(func.min(s.InstitutionField.label)).limit(500)).all()
            result[field]=[{'id':r[0],'name':r[1],'count':r[2]} for r in rows]
        return result

@router.get('/catalog-coverage')
def coverage(user=Depends(current_user)):
    with Session() as db:
        total=db.scalar(select(func.count()).select_from(Publication))
        criteria={'doi':s.WorkMetadata.has_doi.is_(True),'abstract':s.WorkMetadata.has_abstract.is_(True),'language':s.WorkMetadata.language!='','journal':s.WorkMetadata.journal!=''}
        counts={key:db.scalar(select(func.count()).select_from(s.WorkMetadata).where(condition)) for key,condition in criteria.items()}
        counts['crossref']=db.scalar(select(func.count()).select_from(Publication).where(Publication.crossref_at.is_not(None)))
        return {'total':total,'available':counts,'scope':'Disponibilidade de campos no catálogo local; não mede a cobertura total de cada API.'}
