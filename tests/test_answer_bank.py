"""Answer bank: bank-first lookup, fuzzy matching, company scoping, LLM fallback.

Run: pytest tests/test_answer_bank.py -v
"""

import sqlite3

import pytest

from services import answer_bank


@pytest.fixture
def conn():
    return sqlite3.connect(":memory:")


def test_normalize_strips_noise():
    assert answer_bank.normalize("Are you authorized to work in India? *") == "are you authorized to work in india"
    assert answer_bank.normalize("Notice period (required)") == "notice period"


def test_user_answer_is_reused_with_fuzzy_match(conn, monkeypatch):
    monkeypatch.setattr(answer_bank, "_llm_answer", lambda *a: pytest.fail("LLM should not be called"))
    answer_bank.remember(conn, [{"question": "Years of experience with Python?", "answer": "4"}])
    r = answer_bank.answer_questions(conn, [{"id": "a", "question": "Years of experience with Python *", "type": "text"}])
    assert r["answers"] == [{"id": "a", "answer": "4", "source": "bank:user", "confidence": "high"}]
    assert r["from_bank"] == 1


def test_bank_answer_mapped_onto_options(conn, monkeypatch):
    monkeypatch.setattr(answer_bank, "_llm_answer", lambda *a: pytest.fail("LLM should not be called"))
    answer_bank.remember(conn, [{"question": "Do you need visa sponsorship?", "answer": "no"}])
    q = {"id": "v", "question": "Do you need visa sponsorship?", "type": "select", "options": ["Yes", "No"]}
    assert answer_bank.answer_questions(conn, [q])["answers"][0]["answer"] == "No"


def test_company_specific_answers_stay_scoped(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(answer_bank, "_llm_answer",
                        lambda qs, *a: calls.append(qs) or {"answers": [{"id": q["id"], "answer": "LLM text"} for q in qs]})
    answer_bank.remember(conn, [{"question": "Why do you want to join us?", "answer": "Acme's pathology AI is..."}], company="Acme")

    same = answer_bank.answer_questions(conn, [{"id": "1", "question": "Why do you want to join us?"}], company="Acme")
    assert same["answers"][0]["source"] == "bank:user" and not calls

    other = answer_bank.answer_questions(conn, [{"id": "1", "question": "Why do you want to join us?"}], company="Globex")
    assert other["answers"][0]["source"] == "llm" and len(calls) == 1


def test_llm_choice_answers_must_match_an_option(conn, monkeypatch):
    monkeypatch.setattr(answer_bank, "_llm_answer", lambda qs, *a: {"answers": [
        {"id": "s", "answer": "Bachelors"}, {"id": "bad", "answer": "Purple"},
        {"id": "c", "answer": "Python | Rust | Go"}]})
    qs = [
        {"id": "s", "question": "Highest degree", "type": "select", "options": ["High school", "Bachelor's", "Master's"]},
        {"id": "bad", "question": "Pick one", "type": "radio", "options": ["Yes", "No"]},
        {"id": "c", "question": "Languages", "type": "checkbox", "options": ["Python", "Go", "Java"]},
    ]
    got = {a["id"]: a["answer"] for a in answer_bank.answer_questions(conn, qs)["answers"]}
    assert got == {"s": "Bachelor's", "c": "Python | Go"}


def test_llm_answer_never_overwrites_user_answer(conn):
    answer_bank.remember(conn, [{"question": "Notice period", "answer": "30 days"}])
    answer_bank.remember(conn, [{"question": "Notice period", "answer": "90 days"}], source="llm")
    assert answer_bank.lookup(conn, "Notice period")["answer"] == "30 days"


def test_answer_bank_api_roundtrip(client):
    h = {"Authorization": "Bearer " + client.post("/api/auth/register", json={"email": "ab@example.com", "password": "secret123"}).json()["token"]}
    r = client.post("/api/extension/remember-answers", json={"answers": [{"question": "Notice period", "answer": "30 days"}]}, headers=h)
    assert r.json()["saved"] == 1
    bank = client.get("/api/answer-bank", headers=h).json()
    assert bank["total"] == 1
    assert client.delete(f"/api/answer-bank/{bank['answers'][0]['id']}", headers=h).json()["status"] == "ok"
    assert client.post("/api/extension/answer-questions", json={"questions": []}, headers=h).status_code == 400
