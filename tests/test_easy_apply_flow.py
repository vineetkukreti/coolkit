"""Easy Apply prepare → review → finish against a fake LinkedIn modal in a real Chromium.

Nothing touches linkedin.com: requests to the job URL are intercepted and served locally.
Run: pytest tests/test_easy_apply_flow.py -v
"""

import pytest

pw = pytest.importorskip("playwright.sync_api")

from services import auto_apply as aa  # noqa: E402

JOB_URL = "https://www.linkedin.com/jobs/view/123/"

PAGE = """<html><body>
<button aria-label="Easy Apply to Acme" onclick="document.getElementById('s1').hidden=false">Easy Apply</button>
<div id="s1" hidden>
  <label for="phone">Mobile phone number</label><input id="phone" type="text">
  <label for="yrs">How many years of total experience do you have?</label><input id="yrs" type="number">
  <label for="sp">Will you require visa sponsorship?</label>
  <select id="sp"><option value="">Select an option</option><option value="y">Yes</option><option value="n">No</option></select>
  <button aria-label="Continue to next step" onclick="document.getElementById('s1').hidden=true;document.getElementById('s2').hidden=false">Next</button>
</div>
<div id="s2" hidden>
  <fieldset><legend>Are you comfortable working from our Pune office?</legend>
    <input type="radio" id="r1" name="o" value="Yes"><label for="r1">Yes</label>
    <input type="radio" id="r2" name="o" value="No"><label for="r2">No</label></fieldset>
  <label for="why">Why are you a fit for this role?</label><textarea id="why"></textarea>
  <button aria-label="Submit application" onclick="window.__submitted = {
      phone: phone.value, yrs: yrs.value, sp: sp.value, o: (document.querySelector('[name=o]:checked')||{}).value, why: why.value };
      document.body.insertAdjacentHTML('beforeend', '<h2>Your application was sent to Acme</h2><button>Done</button>')">Submit application</button>
  <button aria-label="Dismiss" onclick="document.body.insertAdjacentHTML('beforeend','<button>Discard</button>')">x</button>
</div></body></html>"""


@pytest.fixture
def page(monkeypatch):
    monkeypatch.setattr(aa.time, "sleep", lambda *_: None)
    monkeypatch.setattr(aa, "PROFILE", {**aa.PROFILE, "phone": "+91 99999 00000", "experience_years": 4,
                                        "require_visa": "No"})
    bank = {"are you comfortable working from our pune office?": "Yes"}
    monkeypatch.setattr(aa, "_bank_lookup", lambda q, company: bank.get(q.strip().lower(), ""))
    monkeypatch.setattr(aa, "_llm_answer_question", lambda *a, **k: "")  # no network
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        pg = browser.new_page()
        pg.route(JOB_URL, lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE))
        yield pg
        browser.close()


def test_prepare_fills_every_step_and_stops_before_submit(page):
    job = {"post_url": JOB_URL, "company": "Acme", "role": "AI Engineer"}
    result = aa._easy_apply_prepare(page, job)

    assert result["status"] == "ready"
    assert page.evaluate("window.__submitted") is None  # nothing submitted yet
    by_q = {f["question"]: f for f in result["filled"]}
    assert by_q["How many years of total experience do you have?"]["answer"] == "4"
    assert by_q["Will you require visa sponsorship?"] == {"question": "Will you require visa sponsorship?", "answer": "No", "source": "profile"}
    assert by_q["Are you comfortable working from our Pune office?"]["source"] == "bank"
    # No profile/bank/AI answer: left blank and flagged instead of guessed
    assert by_q["Why are you a fit for this role?"] == {"question": "Why are you a fit for this role?", "answer": "", "source": "missing"}


def test_finish_submit_records_confirmed_application(page):
    job = {"post_url": JOB_URL, "company": "Acme"}
    assert aa._easy_apply_prepare(page, job)["status"] == "ready"
    page.fill("#why", "My clinical NLP work maps to your roadmap.")  # what the user does during review
    assert aa._easy_apply_finish(page, submit=True) == {"status": "applied", "method": "easy_apply"}
    assert page.evaluate("window.__submitted") == {"phone": "+91 99999 00000", "yrs": "4", "sp": "n", "o": "Yes",
                                                   "why": "My clinical NLP work maps to your roadmap."}


def test_finish_skip_discards_without_submitting(page):
    assert aa._easy_apply_prepare(page, {"post_url": JOB_URL, "company": "Acme"})["status"] == "ready"
    assert aa._easy_apply_finish(page, submit=False)["status"] == "skipped"
    assert page.evaluate("window.__submitted") is None


def test_non_linkedin_url_rejected(page):
    assert aa._easy_apply_prepare(page, {"post_url": "https://example.com/job"})["status"] == "failed"


def test_engine_waits_for_review_then_submits(monkeypatch):
    import threading
    import time as _time
    from services import browser_service

    calls = []

    def fake_browser(fn, timeout=60):
        name = getattr(fn, "__name__", "")
        calls.append(name)
        return fn()

    monkeypatch.setattr(browser_service, "_run_on_browser_thread", fake_browser)
    monkeypatch.setattr(aa, "_easy_apply_prepare",
                        lambda page, job: {"status": "ready", "filled": [{"question": "Q", "answer": "", "source": "missing"}]})
    monkeypatch.setattr(aa, "_easy_apply_finish", lambda page, submit: {"status": "applied" if submit else "skipped", "method": "easy_apply"})
    engine = aa.AutoApplyEngine.__new__(aa.AutoApplyEngine)
    engine.page, engine.conn = object(), None
    monkeypatch.setattr(engine, "_remember_answers", lambda job, filled: None, raising=False)
    aa.auto_apply_state["review"] = True

    out = {}
    t = threading.Thread(target=lambda: out.update(engine._easy_apply({"role": "AI Eng", "company": "Acme"})))
    t.start()
    for _ in range(50):
        if aa.auto_apply_state["pending_review"]:
            break
        _time.sleep(0.05)
    pending = aa.get_auto_apply_status()["pending_review"]
    assert pending["job"]["company"] == "Acme" and pending["needs_attention"] == 1
    assert aa.submit_review("submit")["status"] == "ok"
    t.join(timeout=5)
    assert out["status"] == "applied"
    assert aa.auto_apply_state["pending_review"] is None


def test_submit_review_without_pending_is_error():
    aa.auto_apply_state["pending_review"] = None
    assert aa.submit_review("submit")["status"] == "error"
    assert aa.submit_review("maybe")["status"] == "error"
