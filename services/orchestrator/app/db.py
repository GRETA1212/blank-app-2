import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://studio:studio_local_password@localhost:5433/studio",
)
LOCAL_USER_EMAIL = os.getenv("LOCAL_USER_EMAIL", "local@studio.invalid")


@contextmanager
def connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


def ensure_local_identity() -> tuple[str, str]:
    with connection() as conn:
        user = conn.execute(
            """
            insert into app_users (email)
            values (%s)
            on conflict (email) do update set email = excluded.email
            returning id
            """,
            (LOCAL_USER_EMAIL,),
        ).fetchone()
        assert user is not None
        workspace = conn.execute(
            """
            insert into workspaces (user_id, name)
            select %s, 'My Studio'
            where not exists (
              select 1 from workspaces where user_id = %s
            )
            returning id
            """,
            (user["id"], user["id"]),
        ).fetchone()
        if workspace is None:
            workspace = conn.execute(
                "select id from workspaces where user_id = %s order by created_at limit 1",
                (user["id"],),
            ).fetchone()
        assert workspace is not None
        conn.commit()
        return str(user["id"]), str(workspace["id"])


def identity() -> tuple[str, str]:
    return ensure_local_identity()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        return list(conn.execute(query, params).fetchall())


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connection() as conn:
        return conn.execute(query, params).fetchone()


def execute_returning(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(query, params).fetchone()
        conn.commit()
        return row


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount
