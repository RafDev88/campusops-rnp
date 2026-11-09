import hashlib
import os
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import delete, select

from .automation import aware
from .database import Session
from .domain import Audit, LoginLimit, SessionToken, User, utcnow

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash(secrets.token_urlsafe(32))
COOKIE = 'campusops_demo_session' if os.getenv('CAMPUSOPS_DEMO') == 'true' else 'campusops_session'


def public_user(user):
    return {'id': user.id, 'username': user.username, 'role': user.role, 'active': user.active}


def current_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    if not token or len(token) > 200:
        raise HTTPException(401, 'Faça login para continuar.')
    with Session() as db:
        session = db.get(SessionToken, hashlib.sha256(token.encode()).hexdigest())
        if not session or aware(session.expires_at) <= utcnow():
            raise HTTPException(401, 'Sessão expirada. Faça login novamente.')
        user = db.get(User, session.user_id)
        if not user or not user.active:
            raise HTTPException(401, 'Acesso desativado.')
        return public_user(user)


def operator(user=Depends(current_user)):
    if user['role'] not in {'admin', 'operator'}:
        raise HTTPException(403, 'Esta operação exige perfil de operador ou administrador.')
    return user


def admin(user=Depends(current_user)):
    if user['role'] != 'admin':
        raise HTTPException(403, 'Esta operação exige perfil de administrador.')
    return user


def create_session(db, user, response):
    token = secrets.token_urlsafe(48)
    db.execute(delete(SessionToken).where(SessionToken.expires_at < utcnow()))
    db.add(SessionToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                        expires_at=utcnow() + timedelta(hours=8)))
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict', max_age=28800,
                        secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', path='/')


def login(credentials, request: Request, response, issue_session=True):
    identity = f"{request.client.host if request.client else 'local'}:{credentials.username.lower()}"
    key = hashlib.sha256(identity.encode()).hexdigest()
    with Session() as db:
        limit = db.get(LoginLimit, key)
        if limit and aware(limit.until) > utcnow() and limit.count >= 10:
            raise HTTPException(429, 'Muitas tentativas. Aguarde dez minutos.')
        if not limit:
            limit = LoginLimit(key=key, count=0, until=utcnow() + timedelta(minutes=10))
            db.add(limit)
        elif aware(limit.until) <= utcnow():
            limit.count, limit.until = 0, utcnow() + timedelta(minutes=10)
        limit.count += 1
        db.commit()
        user = db.scalar(select(User).where(User.username == credentials.username.lower()))
        valid = passwords.verify(credentials.password, user.password_hash if user else dummy_hash)
        if not user or not valid or not user.active:
            raise HTTPException(401, 'Usuário ou senha inválidos.')
        limit.count = 0
        if issue_session:
            create_session(db, user, response)
            db.add(Audit(actor=user.username, action='auth.login'))
        db.commit()
        return public_user(user)
