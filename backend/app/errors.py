"""Stable additive error fields; validation never echoes passwords or request bodies."""
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

CODES = {400: 'invalid_operation', 401: 'unauthenticated', 403: 'forbidden',
         404: 'not_found', 409: 'conflict', 422: 'validation_error', 429: 'rate_limited'}


def error_response(request, status, detail, headers=None):
    return JSONResponse({'detail': detail, 'code': CODES.get(status, 'internal_error'),
                         'request_id': getattr(request.state, 'request_id', '')}, status_code=status, headers=headers)


def install_errors(app):
    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(request, exc.status_code, exc.detail, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        details = [{key: value for key, value in error.items() if key in {'type','loc','msg'}} for error in exc.errors()]
        return error_response(request, 422, details)
