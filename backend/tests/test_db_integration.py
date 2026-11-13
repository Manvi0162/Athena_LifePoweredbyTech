"""End-to-end through the API into her real SQL functions.

Runs only when a local PostgreSQL is reachable (LB_TEST_PG, default
host=/tmp port=5499 user=postgres). Loads a Supabase stand-in, her schema
(sql/01) and cooking v2 (sql/02) into a fresh database, then calls the API.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

psycopg = pytest.importorskip("psycopg")
from psycopg.types.json import Jsonb  # noqa: E402

import app as app_module  # noqa: E402
from core import auth  # noqa: E402

PG = os.environ.get("LB_TEST_PG", "host=/tmp port=5499 user=postgres")
DB = "lb_api_test"
USER = "71d8eafb-0035-412b-90ac-ad8a7f44f14d"
HOUSEHOLD_ID = "fe951ebe-54ab-42ec-9868-07ee674a90fa"

# Argument types of her functions, so named JSON params can be cast.
SIGNATURES = {
    "confirm_grocery_receipt": {"p_household_id": "uuid", "p_source_identifier": "text",
                                "p_retailer": "text", "p_receipt_date": "date",
                                "p_total": "numeric", "p_items": "jsonb"},
    "lb_save_ai_recipe": {"p_household_id": "uuid", "p_recipe": "jsonb"},
    "lb_confirm_cooking": {"p_household_id": "uuid", "p_recipe_id": "uuid", "p_operation_id": "uuid"},
}


@pytest.fixture(scope="module")
def conn():
    try:
        admin = psycopg.connect(PG + " dbname=postgres", autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("No local PostgreSQL for integration tests")
    admin.execute(f"drop database if exists {DB}")
    admin.execute(f"create database {DB}")
    admin.close()
    c = psycopg.connect(PG + f" dbname={DB}", autocommit=True)
    for f in [ROOT / "tests/sql/supabase_stub.sql", ROOT / "sql/01_livebetter_schema.sql",
              ROOT / "sql/02_lb_confirm_cooking_v2.sql"]:
        c.execute(f.read_text())
    c.execute("grant usage on schema public to authenticated; "
              "grant all on all tables in schema public to authenticated; "
              "revoke all on public.extracted_documents from authenticated;")
    c.execute("insert into auth.users values (%s)", (USER,))
    c.execute("insert into public.households (id, owner_id, name) values (%s, %s, 'Demo')",
              (HOUSEHOLD_ID, USER))
    yield c
    c.close()


class PostgresRPC:
    """Stands in for the Supabase client: rpc() runs the real function as the
    logged-in user (role authenticated + auth.uid())."""

    def __init__(self, conn):
        self.conn = conn

    def rpc(self, name, params):
        conn = self.conn
        sig = SIGNATURES[name]

        class Call:
            def execute(self_inner):
                args = ", ".join(f"{k} => %({k})s::{sig[k]}" for k in params)
                values = {k: Jsonb(v) if sig[k] == "jsonb" else v for k, v in params.items()}
                try:
                    with conn.transaction():
                        conn.execute("set local role authenticated")
                        conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (USER,))
                        row = conn.execute(f"select public.{name}({args})", values).fetchone()
                except psycopg.Error as exc:
                    raise APIError({"message": exc.diag.message_primary, "code": exc.sqlstate})
                return type("Resp", (), {"data": row[0] if not isinstance(row[0], uuid.UUID) else str(row[0])})()
        return Call()


@pytest.fixture
def client(conn):
    db = PostgresRPC(conn)
    app_module.app.dependency_overrides[auth.get_household_context] = (
        lambda: auth.HouseholdContext(user_id=USER, db=db, household={"id": HOUSEHOLD_ID}))
    yield TestClient(app_module.app)
    app_module.app.dependency_overrides.clear()


def pantry(conn):
    rows = conn.execute("select ingredient_name, quantity::float from public.pantry_items "
                        "order by 1").fetchall()
    return dict(rows)


def test_receipt_cook_flow_against_her_sql(client, conn):
    receipt = {"source_identifier": "photo-sha-1", "retailer": "WINNERS", "receipt_date": "2026-11-11",
               "total": 233, "items": [
                   {"normalized_name": "rice", "quantity": 2, "unit": "kg", "line_total": 120},
                   {"normalized_name": "carrots", "quantity": 1, "unit": "kg", "line_total": 65},
                   {"normalized_name": "eggs", "quantity": 6, "unit": "piece", "line_total": 48}]}

    # Confirm the receipt twice: same receipt id, pantry filled once.
    first = client.post("/receipts/confirm", json=receipt)
    assert first.status_code == 200, first.text
    second = client.post("/receipts/confirm", json=receipt)
    assert first.json() == second.json()
    assert pantry(conn) == {"carrots": 1.0, "eggs": 6.0, "rice": 2.0}

    # Save an AI draft.
    draft = {"name": "Fried Rice", "instructions": ["fry"], "ingredients": [
        {"ingredient_name": "rice", "quantity": 500, "unit": "g"},
        {"ingredient_name": "carrots", "quantity": 0.3, "unit": "kg"},
        {"ingredient_name": "eggs", "quantity": 4, "unit": "piece"},
        {"ingredient_name": "water", "quantity": 1, "unit": "l"},
        {"ingredient_name": "cooking oil", "quantity": 30, "unit": "ml"}]}
    saved = client.post("/recipes/drafts", json={"recipe": draft})
    assert saved.status_code == 200, saved.text
    recipe_id = saved.json()["recipe_id"]

    # Cook it: 500 g rice comes off the kg stock; water and oil skipped.
    op = str(uuid.uuid4())
    cooked = client.post(f"/recipes/{recipe_id}/cook", json={"operation_id": op}).json()
    assert cooked["status"] == "confirmed" and cooked["ingredients_deducted"] == 3
    assert {s["ingredient"] for s in cooked["skipped"]} == {"water", "cooking oil"}
    assert pantry(conn) == {"carrots": 0.7, "eggs": 2.0, "rice": 1.5}

    # Same tap again: nothing deducted twice.
    again = client.post(f"/recipes/{recipe_id}/cook", json={"operation_id": op}).json()
    assert again["status"] == "already_confirmed"
    assert pantry(conn) == {"carrots": 0.7, "eggs": 2.0, "rice": 1.5}

    # Cook again for real: only 2 eggs left, so 409 and the pantry is unchanged.
    short = client.post(f"/recipes/{recipe_id}/cook", json={"operation_id": str(uuid.uuid4())})
    assert short.status_code == 409
    assert "Insufficient ingredient: eggs" in short.json()["detail"]["message"]
    assert pantry(conn) == {"carrots": 0.7, "eggs": 2.0, "rice": 1.5}


def test_invalid_receipt_unit_rejected_by_her_sql(client):
    bad = {"source_identifier": "photo-sha-2", "total": 10,
           "items": [{"normalized_name": "tea", "quantity": 1, "unit": "box"}]}
    resp = client.post("/receipts/confirm", json=bad)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_input"


def test_non_food_line_never_reaches_pantry(client, conn):
    before = pantry(conn)
    resp = client.post("/receipts/confirm", json={
        "source_identifier": "photo-sha-3", "total": 120, "items": [
            {"normalized_name": "flour", "quantity": 1, "unit": "kg", "line_total": 60, "category": "food"},
            {"normalized_name": "aa batteries", "quantity": 2, "unit": "piece", "line_total": 60,
             "category": "non_food"}]})
    assert resp.status_code == 200, resp.text
    after = pantry(conn)
    assert after.get("flour") == before.get("flour", 0) + 1
    assert "aa batteries" not in after
    total = conn.execute("select total::float from public.grocery_receipts "
                         "where source_identifier = 'photo-sha-3'").fetchone()[0]
    assert total == 60.0
