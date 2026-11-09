"""Prevent the published integration contract from hiding real access requirements."""
from app.api_documentation import access_level, api_routes
from app.main import app


def test_every_operation_documents_session_roles_and_csrf():
    schema = app.openapi()
    checked = set()
    for route in api_routes(app):
        role = access_level(route.dependant)
        for method in route.methods:
            operation = schema['paths'][route.path][method.lower()]
            checked.add((route.path, method.lower()))
            assert operation['x-access-level'] == ('public', 'viewer', 'operator', 'admin')[role]
            assert bool(operation.get('security')) == bool(role)
            csrf = [p for p in operation.get('parameters', []) if p['name'] == 'X-CampusOps']
            assert bool(csrf) == (method not in {'GET', 'HEAD', 'OPTIONS'})
    assert checked == {(path, method) for path, operations in schema['paths'].items()
                       for method in operations if method in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}}
    assert schema['paths']['/api/users']['post']['x-access-level'] == 'admin'
    assert schema['paths']['/api/sync']['post']['x-access-level'] == 'operator'
    assert schema['paths']['/api/saved-searches']['post']['x-access-level'] == 'viewer'


def test_documentation_is_public_but_does_not_bypass_security(client):
    assert client.get('/openapi.json').status_code == 200
    assert client.get('/docs').status_code == 200
    assert client.get('/api/publications').status_code == 401
    response = client.post('/api/auth/login', headers={'X-CampusOps': 'invalid'},
                           json={'username': 'example', 'password': 'example-password'})
    assert response.status_code == 403
