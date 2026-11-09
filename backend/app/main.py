import hashlib
import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from . import domain as d
from .database import Session
from .migrate import migrate
from .schemas import Credentials, Toggle, UserCreate
from .security import COOKIE, admin, create_session, current_user, login, passwords, public_user

structlog.configure(processors=[structlog.contextvars.merge_contextvars,
    structlog.processors.TimeStamper(fmt='iso'), structlog.processors.JSONRenderer()])
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app):
    migrate()
    with Session() as db:
        if not db.scalar(select(d.Rule.id).limit(1)):
            db.add_all([
                d.Rule(name='Três falhas consecutivas', kind='failure_streak', source='all', threshold=3),
                d.Rule(name='Mudança de contrato', kind='schema_change', source='all', threshold=1),
            ])
            db.commit()
        from .job_runtime import policy
        for source in ['ror','openalex','crossref','orcid','ufrn']:policy(db,source)
        db.commit()
    from .monitor_inventory import sync_inventory
    sync_inventory()
    yield


app = FastAPI(title='CampusOps API', version='0.8.0', lifespan=lifespan, description="""
Backend do catálogo universitário CampusOps. As pesquisas consultam dados já importados;
as coletas, relatórios e verificações de links são processados em filas Celery.

**Acesso:** faça login com sua conta existente em `POST /api/auth/login`.
O setup só está disponível quando ainda não existe usuário. Sessões usam cookie HttpOnly
com validade de oito horas. Toda escrita exige `X-CampusOps: 1`, inclusive login e setup.
Use a documentação e o login na mesma origem (por exemplo, localhost:8000).

**Permissões:** consulta (viewer), operador (operator) e administrador (admin).
Favoritos, pesquisas salvas, avisos e relatórios respeitam a propriedade da conta.
`202` confirma enfileiramento, não conclusão; acompanhe a execução pelo identificador.
""")


@app.middleware('http')
async def request_context(request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = perf_counter()
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and request.headers.get('X-CampusOps') != '1':
        from .errors import error_response
        response = error_response(request, 403, 'Cabeçalho de proteção CSRF ausente.')
    else:
        try:
            response = await call_next(request)
        except Exception as exc:
            from .errors import error_response
            logger.error('unhandled_request_error', error_type=type(exc).__name__)
            response = error_response(request, 500, 'Não foi possível concluir a operação. Informe o identificador da requisição ao suporte.')
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    logger.info('http_request', method=request.method, path=request.url.path,
                status=response.status_code, duration_ms=int((perf_counter() - start) * 1000))
    return response


@app.get('/api/health')
def health():
    with Session() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok'}


@app.get('/api/auth/status')
def auth_status():
    with Session() as db:
        return {'setup_required': db.scalar(select(func.count()).select_from(d.User)) == 0,
                'demo_mode': os.getenv('CAMPUSOPS_DEMO') == 'true'}


@app.post('/api/auth/setup')
def setup(credentials: Credentials, response: Response):
    with Session() as db:
        if db.scalar(select(d.User.id).limit(1)):
            raise HTTPException(409, 'A conta inicial já foi criada.')
        user = d.User(id=1, username=credentials.username.lower(), password_hash=passwords.hash(credentials.password), role='admin')
        db.add(user)
        try:
            db.flush()
            if db.bind.dialect.name == 'postgresql':
                db.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users))"))
            create_session(db, user, response)
            db.add(d.Audit(actor=user.username, action='auth.setup'))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'A conta inicial já foi criada.') from None
        return public_user(user)


@app.post('/api/auth/login')
def sign_in(credentials: Credentials, request: Request, response: Response):
    return login(credentials, request, response)


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, user=Depends(current_user)):
    with Session() as db:
        token = db.get(d.SessionToken, hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest())
        if token:
            db.delete(token)
        db.add(d.Audit(actor=user['username'], action='auth.logout'))
        db.commit()
    response.delete_cookie(COOKIE)
    return {'ok': True}


@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return user


@app.get('/api/users')
def users(user=Depends(admin)):
    with Session() as db:
        return [public_user(row) for row in db.scalars(select(d.User).order_by(d.User.id))]


@app.post('/api/users', status_code=201)
def create_user(payload: UserCreate, user=Depends(admin)):
    with Session() as db:
        new = d.User(username=payload.username.lower(), password_hash=passwords.hash(payload.password), role=payload.role)
        db.add(new)
        db.add(d.Audit(actor=user['username'], action='user.created', detail={'username': new.username, 'role': new.role}))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Nome de usuário já cadastrado.') from None
        return public_user(new)


@app.patch('/api/users/{identifier}')
def toggle_user(identifier: int, payload: Toggle, user=Depends(admin)):
    if identifier == user['id']:
        raise HTTPException(400, 'Você não pode desativar a própria conta.')
    with Session() as db:
        target = db.get(d.User, identifier)
        if not target:
            raise HTTPException(404, 'Usuário não encontrado.')
        target.active = payload.enabled
        db.add(d.Audit(actor=user['username'], action='user.toggled', detail={'id': identifier, 'active': payload.enabled}))
        db.commit()
        return public_user(target)


from .read_api import router as read_router
from .write_api import router as write_router
app.include_router(read_router, prefix='/api')
app.include_router(write_router, prefix='/api')
from .discovery_api import router as discovery_router
app.include_router(discovery_router, prefix='/api')
from .orchestration_api import router as orchestration_router
app.include_router(orchestration_router, prefix='/api')
from .catalog_api import router as catalog_router
app.include_router(catalog_router,prefix='/api')
from .monitor_api import router as monitor_router
app.include_router(monitor_router,prefix='/api')

from .api_documentation import install_openapi
from .reliability_api import router as reliability_router
from .account_api import router as account_router
from .errors import install_errors
app.include_router(reliability_router, prefix='/api')
app.include_router(account_router, prefix='/api')
install_errors(app)
install_openapi(app)
