"""OpenAPI annotations derived from the real dependency graph; no access changes."""
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from .security import COOKIE, admin, current_user, operator

GROUPS = {
    'main': 'Acesso e sistema', 'read_api': 'Consultas operacionais',
    'write_api': 'Comandos operacionais', 'discovery_api': 'Pesquisa e biblioteca pessoal',
    'orchestration_api': 'Fluxos, agendas e relatórios',
    'catalog_api': 'Catálogo e cobertura', 'monitor_api': 'Saúde das fontes e links',
    'reliability_api': 'Confiabilidade e acompanhamento', 'account_api': 'Minha conta',
}


def api_routes(app):
    """Include lazily mounted routers on current FastAPI and older eager routers."""
    try:
        from fastapi.routing import iter_route_contexts
    except ImportError:
        yield from (route for route in app.routes if isinstance(route, APIRoute))
    else:
        yield from (route for route in iter_route_contexts(app.routes)
                    if isinstance(route.original_route, APIRoute))


def access_level(dependency):
    """Choose the strongest role, including nested FastAPI dependencies."""
    levels = {current_user: 1, operator: 2, admin: 3}
    return max([levels.get(dependency.call, 0)] +
               [access_level(child) for child in dependency.dependencies])


def install_openapi(app):
    def documented_schema():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version,
                             description=app.description, routes=app.routes)
        from .contracts import ErrorResponse
        error_schema = ErrorResponse.model_json_schema()
        schema.setdefault('components', {}).setdefault('schemas', {})['ErrorResponse'] = error_schema
        schema.setdefault('components', {}).setdefault('securitySchemes', {})['SessionCookie'] = {
            'type': 'apiKey', 'in': 'cookie', 'name': COOKIE,
            'description': 'Faça login em /api/auth/login. O navegador recebe um cookie HttpOnly; '
                           'use o Swagger na mesma origem da sessão. Não há token Bearer.',
        }
        for route in api_routes(app):
            role = access_level(route.dependant)
            for method in route.methods:
                operation = schema['paths'][route.path][method.lower()]
                operation['tags'] = [GROUPS.get(route.endpoint.__module__.split('.')[-1], 'Sistema')]
                operation['x-access-level'] = ('public', 'viewer', 'operator', 'admin')[role]
                if role:
                    operation['security'] = [{'SessionCookie': []}]
                    operation.setdefault('responses', {}).setdefault('401', {'description': 'Sessão ausente, expirada ou conta desativada.'})
                if role >= 2:
                    operation['responses'].setdefault('403', {'description': 'Perfil sem permissão para esta operação.'})
                if method not in {'GET', 'HEAD', 'OPTIONS'}:
                    operation.setdefault('parameters', []).append({
                        'name': 'X-CampusOps', 'in': 'header', 'required': True,
                        'schema': {'type': 'string', 'enum': ['1'], 'default': '1'},
                        'description': 'Proteção CSRF obrigatória, inclusive no login e setup.',
                    })
                    operation['responses'].setdefault('403', {'description': 'Cabeçalho CSRF ausente/inválido ou perfil sem permissão.'})
                note = ('Público.' if not role else
                        'Perfil mínimo: ' + ('', 'consulta (viewer)', 'operador (operator)', 'administrador (admin)')[role] +
                        '. Restrições de propriedade do recurso também se aplicam.')
                operation['description'] = (operation.get('description', '') + '\n\n' + note).strip()
                for status in ('400','401','403','404','409','422','429'):
                    if status in operation.get('responses', {}):
                        operation['responses'][status]['content'] = {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'}}}
        app.openapi_schema = schema
        return schema

    app.openapi = documented_schema
