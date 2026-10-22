"""End-to-end API tests against a real database: accounts, uploads, search, answers,
and, most importantly, that users can never see each other's documents.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

PASSWORD = "correct horse battery"

HANDBOOK = b"""# Handbook

Full-time employees receive 20 days of paid time off each year.
Unused time off can be carried over, up to a maximum of 5 days.
"""


def sign_up(client: TestClient) -> str:
    """Creates a unique account on this client (which keeps the session cookie)."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201
    return email


def upload(client: TestClient, content: bytes = HANDBOOK, filename: str = "handbook.md") -> dict:
    response = client.post("/documents", files={"file": (filename, content, "text/markdown")})
    assert response.status_code == 201
    return response.json()


# ---- Accounts --------------------------------------------------------------

def test_sign_up_signs_you_in_with_an_httponly_cookie(make_client):
    client = make_client()
    response = client.post(
        "/auth/register", json={"email": f"new-{uuid.uuid4().hex[:8]}@example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").json()["email"] == response.json()["email"]


def test_duplicate_email_is_rejected(make_client):
    client = make_client()
    email = sign_up(client)

    response = make_client().post("/auth/register", json={"email": email, "password": PASSWORD})

    assert response.status_code == 409


def test_wrong_password_and_unknown_email_get_the_same_error(make_client):
    email = sign_up(make_client())

    wrong_password = make_client().post("/auth/login", json={"email": email, "password": "wrong password"})
    unknown_email = make_client().post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_sign_out_ends_the_session(make_client):
    client = make_client()
    sign_up(client)

    client.post("/auth/logout")

    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/documents"), ("POST", "/search"), ("POST", "/ask"), ("GET", "/auth/me")],
)
def test_endpoints_require_sign_in(make_client, method, path):
    response = make_client().request(method, path, json={"query": "x", "question": "x"})

    assert response.status_code == 401


# ---- Documents ---------------------------------------------------------------

def test_upload_is_chunked_embedded_and_listed(make_client):
    client = make_client()
    sign_up(client)

    document = upload(client)

    assert document["status"] == "ready"
    assert document["chunk_count"] >= 1
    assert [d["id"] for d in client.get("/documents").json()] == [document["id"]]
    chunks = client.get(f"/documents/{document['id']}/chunks").json()
    assert "20 days of paid time off" in chunks[0]["content"]


def test_unsupported_file_type_is_rejected(make_client):
    client = make_client()
    sign_up(client)

    response = client.post("/documents", files={"file": ("photo.png", b"not text", "image/png")})

    assert response.status_code == 415


def test_delete_removes_the_document(make_client):
    client = make_client()
    sign_up(client)
    document = upload(client)

    assert client.delete(f"/documents/{document['id']}").status_code == 204
    assert client.get(f"/documents/{document['id']}").status_code == 404
    assert client.get("/documents").json() == []


# ---- Search and answers -------------------------------------------------------

def test_search_finds_the_relevant_passage(make_client):
    client = make_client()
    sign_up(client)
    upload(client)

    results = client.post("/search", json={"query": "How much vacation do I get?"}).json()

    assert results
    assert "20 days" in results[0]["content"]


class FakeLLM:
    def stream(self, system, prompt):
        yield "You get 20 days [1]."


def test_ask_streams_sources_then_answer_then_done(make_client, monkeypatch):
    monkeypatch.setattr("app.routers.ask.get_llm", lambda: FakeLLM())
    client = make_client()
    sign_up(client)
    upload(client)

    response = client.post("/ask", json={"question": "How many days of paid time off do I get?"})
    body = response.text

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.index("event: sources") < body.index("event: token") < body.index("event: done")
    assert "handbook.md" in body
    assert "You get 20 days [1]." in body


# ---- Isolation between users ------------------------------------------------

def test_users_cannot_see_each_others_documents(make_client, monkeypatch):
    alice, bob = make_client(), make_client()
    sign_up(alice)
    sign_up(bob)
    alices_document = upload(alice)
    document_url = f"/documents/{alices_document['id']}"

    # Bob's list is empty, and Alice's document looks like it doesn't exist.
    assert bob.get("/documents").json() == []
    assert bob.get(document_url).status_code == 404
    assert bob.get(f"{document_url}/chunks").status_code == 404
    assert bob.delete(document_url).status_code == 404

    # Searching and asking with Alice's exact words finds nothing of hers.
    assert bob.post("/search", json={"query": "20 days of paid time off"}).json() == []
    monkeypatch.setattr("app.routers.ask.get_llm", lambda: FakeLLM())
    answer = bob.post("/ask", json={"question": "How many days of paid time off?"}).text
    assert "handbook.md" not in answer
    assert "couldn't find this" in answer

    # And Alice's document is untouched.
    assert alice.get(document_url).status_code == 200