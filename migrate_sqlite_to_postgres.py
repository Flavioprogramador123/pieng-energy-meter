#!/usr/bin/env python3
"""
Migra os dados REAIS do SQLite local (data/app.db) para o Postgres de teste
(docker-compose.yml). Não gera nenhum dado sintético - só copia o que já foi
coletado de hardware real.

Preserva os IDs originais (para manter as foreign keys corretas) e ajusta as
sequences do Postgres no final, para que os próximos INSERTs continuem a
partir do maior ID já usado.

Uso:
    python migrate_sqlite_to_postgres.py [--postgres-url URL]
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app import models  # noqa: F401  (garante que todos os models sejam registrados no Base.metadata)

load_dotenv()

SQLITE_URL = "sqlite:///./data/app.db"

# Ordem importa: tabelas pai antes das filhas (FKs)
TABLE_ORDER = [
    models.Client,
    models.Device,
    models.Measurement,
    models.AlarmRuleModel,
    models.AlarmEvent,
]


def migrate(postgres_url: str):
    sqlite_engine = create_engine(SQLITE_URL)
    postgres_engine = create_engine(postgres_url)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    print("=" * 70)
    print("   MIGRACAO SQLite -> Postgres (dados REAIS)")
    print("=" * 70)

    print(f"\nOrigem:  {SQLITE_URL}")
    print(f"Destino: {postgres_url.split('@')[-1] if '@' in postgres_url else postgres_url}")

    print("\nCriando schema no Postgres (se ainda nao existir)...")
    Base.metadata.create_all(bind=postgres_engine)

    sqlite_db = SqliteSession()
    postgres_db = PostgresSession()

    try:
        for model in TABLE_ORDER:
            table_name = model.__tablename__
            rows = sqlite_db.query(model).order_by(model.id).all()

            if not rows:
                print(f"  {table_name}: 0 registros (nada a migrar)")
                continue

            copied = 0
            skipped = []
            for row in rows:
                data = {c.key: getattr(row, c.key) for c in inspect(model).mapper.column_attrs}
                try:
                    with postgres_db.begin_nested():
                        # merge com PK explicita preserva o ID original
                        postgres_db.merge(model(**data))
                    copied += 1
                except Exception as e:
                    skipped.append((data.get("id"), str(e).splitlines()[0]))

            postgres_db.commit()
            print(f"  {table_name}: {copied} registros migrados")
            if skipped:
                print(f"    [AVISO] {len(skipped)} registro(s) pulado(s) por dado invalido/corrompido:")
                for row_id, err in skipped:
                    print(f"      - id={row_id}: {err}")

        print("\nAjustando sequences do Postgres para o proximo ID livre...")
        for model in TABLE_ORDER:
            table_name = model.__tablename__
            with postgres_engine.begin() as conn:
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), "
                    f"(SELECT MAX(id) IS NOT NULL FROM {table_name}))"
                ))
        print("Sequences ajustadas.")

        print("\n" + "=" * 70)
        print("   MIGRACAO CONCLUIDA")
        print("=" * 70)
        print("\nProximo passo: trocar DATABASE_URL no .env para o Postgres")
        print("e reiniciar a aplicacao para validar.")

    finally:
        sqlite_db.close()
        postgres_db.close()


if __name__ == "__main__":
    default_url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'energy_meter')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'energy_meter_dev_only')}@"
        f"localhost:5432/{os.getenv('POSTGRES_DB', 'energy_meter')}"
    )
    postgres_url = sys.argv[1] if len(sys.argv) > 1 else default_url

    migrate(postgres_url)
