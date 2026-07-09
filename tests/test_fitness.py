"""Tests for fitness filtering logic used by paste-extract and scrapers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from extractors.fitness import is_relevant_role, is_good_fit, experience_to_years


class TestIsRelevantRole:
    def test_ai_ml_roles_are_relevant(self):
        roles = [
            "AI Engineer",
            "ML Engineer",
            "Machine Learning Engineer",
            "GenAI Engineer",
            "LLM Engineer",
            "Deep Learning Engineer",
            "Agentic AI Engineer",
            "MLOps Engineer",
            "AI Researcher",
            "Applied Scientist",
        ]
        for role in roles:
            assert is_relevant_role(role) is True, f"{role} should be relevant"

    def test_ai_subfield_roles_are_relevant(self):
        # These were previously in FALSE_POSITIVE_ROLES and incorrectly rejected.
        assert is_relevant_role("NLP Engineer") is True
        assert is_relevant_role("Computer Vision Engineer") is True
        assert is_relevant_role("CV Engineer") is True
        assert is_relevant_role("LLM Research Scientist") is True

    def test_ai_roles_with_false_positive_substrings_stay_relevant(self):
        # The keep-list should be checked first so roles like "AI Backend Engineer"
        # are not rejected just because they contain "backend".
        assert is_relevant_role("AI Backend Engineer") is True
        assert is_relevant_role("Full Stack AI Engineer") is True
        assert is_relevant_role("Python AI Developer") is True

    def test_non_technical_and_unrelated_roles_are_not_relevant(self):
        roles = [
            "Java Developer",
            "Frontend Developer",
            "Sales Manager",
            "HR Executive",
            "Nurse",
            "Product Manager",
        ]
        for role in roles:
            assert is_relevant_role(role) is False, f"{role} should not be relevant"

    def test_data_roles_remain_not_relevant(self):
        # Data Scientist/Analyst/Engineer are adjacent but distinct from the AI
        # Engineer profile, so they stay in the false-positive list.
        assert is_relevant_role("Data Scientist") is False
        assert is_relevant_role("Data Analyst") is False
        assert is_relevant_role("Data Engineer") is False


class TestExperienceToYears:
    def test_parses_ranges(self):
        assert experience_to_years("2-4 years") == (2, 4)
        assert experience_to_years("4-6Years") == (4, 6)

    def test_parses_single_values(self):
        assert experience_to_years("2+ years") == (2, 4)
        assert experience_to_years("3 years") == (3, 3)

    def test_parses_fresher(self):
        assert experience_to_years("fresher") == (0, 0)
        assert experience_to_years("0 years") == (0, 0)

    def test_returns_none_for_missing(self):
        assert experience_to_years("") == (None, None)


class TestIsGoodFit:
    def test_relevant_role_with_no_experience_is_fit(self):
        assert is_good_fit("AI Engineer", "") == (True, "ok")

    def test_relevant_role_mid_level_is_fit(self):
        # 4-5 year roles should be fit for a 2-year AI Engineer.
        assert is_good_fit("AI Engineer", "4-6 years") == (True, "ok")
        assert is_good_fit("AI Engineer", "3-5 years") == (True, "ok")
        assert is_good_fit("AI Engineer", "2+ years") == (True, "ok")

    def test_fresher_only_roles_are_not_fit(self):
        assert is_good_fit("AI Engineer", "fresher") == (False, "fresher-only")
        assert is_good_fit("AI Engineer", "0 years") == (False, "fresher-only")

    def test_too_senior_roles_are_not_fit(self):
        assert is_good_fit("AI Engineer", "6+ years") == (False, "too-senior:6yr+")
        assert is_good_fit("AI Engineer", "8-10 years") == (False, "too-senior:8yr+")

    def test_irrelevant_role_is_not_fit(self):
        fit, reason = is_good_fit("Java Developer", "2 years")
        assert fit is False
        assert reason.startswith("irrelevant-role")
