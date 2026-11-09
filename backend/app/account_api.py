"""Own-account operations; session identifiers are not bearer credentials."""
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select

from .contracts import MessageResponse, PasswordChange, SessionList
from .database import Session
from .domain import Audit, SessionToken, User, utcnow
from .security import COOKIE, create_session, current_user, passwords

router = APIRouter()


def session_id(token_hash):
    return hashlib.sha256(token_hash.encode()).hexdigest()


@router.get('/account/sessions', response_model=SessionList)
def sessions(request: Request, user=Depends(current_user)):
    current = hashlib.sha256(request.cookies.get(COOKIE, '').encode()).hexdigest()
    with Session() as db:
        rows = db.scalars(select(SessionToken).where(SessionToken.user_id == user['id'], SessionToken.expires_at > utcnow()).order_by(SessionToken.expires_at.desc()))
        return {'items': [dict(id=session_id(row.token_hash), current=row.token_hash == current, expires_at=row.expires_at) for row in rows]}


@router.delete('/account/sessions/{identifier}', response_model=MessageResponse)
def revoke(identifier: str, user=Depends(current_user)):
    with Session() as db:
        row = next((row for row in db.scalars(select(SessionToken).where(SessionToken.user_id == user['id']))
                    if session_id(row.token_hash) == identifier), None)
        if not row:
            raise HTTPException(404, 'Sessão não encontrada.')
        db.delete(row)
        db.add(Audit(actor=user['username'], action='auth.session_revoked'))
        db.commit()
        return {'message': 'Sessão encerrada.'}


@router.post('/account/password', response_model=MessageResponse)
def change_password(payload: PasswordChange, request: Request, response: Response, user=Depends(current_user)):
    # Reuse the persistent authentication limiter rather than allowing unlimited hash checks.
    from .security import login
    from .schemas import Credentials
    if payload.current_password == payload.new_password:
        raise HTTPException(400, 'Escolha uma senha diferente da atual.')
    # login applies the IP/account limit and verifies the current password.
    try:
        login(Credentials(username=user['username'], password=payload.current_password), request, Response(), issue_session=False)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise HTTPException(400, 'A senha atual não confere.') from None
        raise
    with Session() as db:
        target = db.scalar(select(User).where(User.id == user['id']).with_for_update())
        # Check again inside the lock in case a concurrent change won the race.
        if not passwords.verify(payload.current_password, target.password_hash):
            raise HTTPException(409, 'A senha foi alterada por outra sessão. Faça login novamente.')
        target.password_hash = passwords.hash(payload.new_password)
        db.execute(delete(SessionToken).where(SessionToken.user_id == user['id']))
        create_session(db, target, response)
        db.add(Audit(actor=user['username'], action='auth.password_changed'))
        db.commit()
    return {'message': 'Senha alterada. As sessões anteriores foram encerradas.'}
