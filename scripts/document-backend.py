"""Generate reference tables from code without startup, migrations or database writes.

Run from the repository root: .venv/Scripts/python scripts/document-backend.py
Use --check in CI to detect stale documentation.
"""
import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.api_documentation import access_level, api_routes
from app.main import app
from app.database import Base


def reference():
    schema = app.openapi()
    lines = ['# Referência gerada do backend', '',
             'Gerado por `scripts/document-backend.py`. Não editar as tabelas manualmente.', '',
             'O gerador importa o aplicativo sem executar seu lifespan: não aplica migrações, '
             'não conecta ao banco e não inicia tarefas. O OpenAPI é a referência de parâmetros '
             'e validações. Permissões abaixo são o mínimo da dependência; propriedade e '
             'regras específicas também são verificadas dentro dos handlers.', '',
             '## Operações HTTP', '', '| Método | Caminho | Perfil mínimo | Módulo / função |',
             '| --- | --- | --- | --- |']
    operations = []
    for route in api_routes(app):
        for method in sorted(route.methods):
            operations.append((route.path, method, route))
    for path, method, route in sorted(operations, key=lambda row: row[:2]):
        role = ('público', 'consulta', 'operador', 'administrador')[access_level(route.dependant)]
        lines.append(f'| {method} | `{path}` | {role} | `{route.endpoint.__module__}.{route.endpoint.__name__}` |')
    lines += ['', f'Total: **{len(operations)} operações**. '
              'Escritas exigem `X-CampusOps: 1`, inclusive setup/login e comandos de consulta via POST.', '',
              '## Tabelas e classes persistidas', '',
              'Inventário dos modelos declarativos, incluindo o histórico legado. '
              'Colunas, índices e constraints estão nos modelos e nas migrações Alembic.', '',
              '| Tabela | Classe | Arquivo |', '| --- | --- | --- |']
    for file in sorted((ROOT / 'backend/app').glob('*.py')):
        tree = ast.parse(file.read_text(encoding='utf-8'))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for field in node.body:
                if isinstance(field, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__tablename__' for t in field.targets):
                    lines.append(f'| `{ast.literal_eval(field.value)}` | `{node.name}` | `app/{file.name}` |')
    lines += ['', '## Filtros de publicações', '',
              'Defaults e limites vêm de `PublicationFilters`; os booleanos opcionais '
              'distinguem ausência, `true` e `false`.', '',
              '| Parâmetro | Padrão | Schema |', '| --- | --- | --- |']
    for parameter in schema['paths']['/api/publications']['get']['parameters']:
        if parameter['in'] != 'query':
            continue
        import json
        definition = parameter['schema']
        encoded = json.dumps(definition, ensure_ascii=False).replace('|', '&#124;')
        lines.append(f"| `{parameter['name']}` | `{json.dumps(definition.get('default'), ensure_ascii=False)}` | `{encoded}` |")
    return '\n'.join(lines) + '\n'


def data_dictionary():
    lines = ['# Dicionário de dados gerado', '',
             'Extraído do metadata SQLAlchemy, sem consultar o banco. '
             'As migrações Alembic determinam a evolução do schema instalado. '
             'Tipos exibidos são os declarados pelo ORM; o dialeto pode adaptá-los.', '',
             'PK = chave primária. FK = chave estrangeira. '
             'Campos nullable aceitam ausência; isso não autoriza omitir campos exigidos pela API.', '']
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        lines += [f'## `{table.name}`', '', '| Coluna | Tipo | Aceita nulo | PK | FK |',
                  '| --- | --- | --- | --- | --- |']
        for column in table.columns:
            foreign = ', '.join(sorted(key.target_fullname for key in column.foreign_keys)) or '—'
            lines.append(f"| `{column.name}` | `{column.type}` | {'sim' if column.nullable else 'não'} | {'sim' if column.primary_key else '—'} | {foreign} |")
        constraints = sorted(', '.join(column.name for column in constraint.columns)
                             for constraint in table.constraints if constraint.__class__.__name__ == 'UniqueConstraint')
        if constraints:
            lines += ['', 'Unicidade adicional: ' + '; '.join(f'`{columns}`' for columns in constraints) + '.']
        if table.indexes:
            lines += ['', 'Índices declarados no ORM: ' + ', '.join(f'`{index.name}`' for index in sorted(table.indexes, key=lambda item: item.name)) + '.']
        lines += ['']
    lines += ['Índices específicos PostgreSQL (GIN/trigramas/expressões) também podem ser '
              'criados pelas migrações e não aparecem integralmente no metadata do ORM.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, content in [('reference.md', reference()), ('data-dictionary.md', data_dictionary())]:
        target = ROOT / 'docs/backend' / name
        if args.check:
            if not target.exists() or target.read_text(encoding='utf-8') != content:
                raise SystemExit(f'{name} desatualizado. Execute scripts/document-backend.py.')
            print(f'OK: {name}')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8', newline='\n')
            print(f'Gerado: docs/backend/{name}')
