"""Reproducible local query benchmark with fictitious records; no main database/broker.

Results are diagnostic, not a production SLA. Run from the repository root.
"""
import argparse
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=int, default=5000)
    args = parser.parse_args()
    if not 100 <= args.records <= 100000:
        parser.error('--records must be between 100 and 100000')
    with tempfile.TemporaryDirectory(prefix='campusops-benchmark-') as directory:
        os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(directory) / 'benchmark.db').as_posix()
        os.environ['REDIS_URL'] = 'memory://'
        from app.migrate import migrate
        from app.database import Session, engine
        from app.domain import Publication
        from app.discovery_models import SearchDocument
        from app.discovery import PublicationFilters, publication_query
        from sqlalchemy import func, select
        migrate()
        with Session() as db:
            db.execute(Publication.__table__.insert(), [dict(id=f'qa:{i}',openalex_id=f'qa:{i}',title=f'Pesquisa de redes {i}',year=2025) for i in range(args.records)])
            db.execute(SearchDocument.__table__.insert(), [dict(kind='publication',entity_id=f'qa:{i}',source='QA',title=f'Pesquisa de redes {i}',normalized_title=f'pesquisa de redes {i}',body=f'pesquisa de redes {i}') for i in range(args.records)])
            db.commit()
        samples = []
        with Session() as db:
            for _ in range(21):
                start = perf_counter()
                query = publication_query(db, PublicationFilters(q='redes',year_from=2024), 0)
                assert db.scalar(select(func.count()).select_from(query.subquery())) == args.records
                assert len(db.scalars(query.limit(25)).all()) == 25
                samples.append((perf_counter()-start)*1000)
        engine.dispose()
        samples = sorted(samples[1:])  # One warm-up is excluded.
        output = {'database':'isolated SQLite','records':args.records,'samples':len(samples),
                  'median_ms':round(statistics.median(samples),2),'p95_ms':round(samples[18],2),
                  'scope':'Count plus first 25 matches using the real query builder; not HTTP, PostgreSQL, concurrency or production load.'}
        destination = ROOT / 'frontend/artifacts/search-benchmark.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(output,indent=2),encoding='utf-8')
        print(json.dumps(output,indent=2))


if __name__ == '__main__':
    main()
