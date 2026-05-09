import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

rich_module = types.ModuleType("rich")
rich_console_module = types.ModuleType("rich.console")


class FakeConsole:
    def print(self, *args, **kwargs):
        pass


rich_console_module.Console = FakeConsole
sys.modules.setdefault("rich", rich_module)
sys.modules.setdefault("rich.console", rich_console_module)

db_module = types.ModuleType("db")
db_module.content_hash = lambda content: content
db_module.post_exists = lambda *args, **kwargs: False
db_module.DedupCache = object
sys.modules.setdefault("db", db_module)

post_parser_module = types.ModuleType("post_parser")
for name in [
    "llm_extract", "extract_roles", "extract_location", "extract_experience",
    "extract_emails", "score_domain_relevance", "is_hiring_post", "is_good_fit",
    "normalize_experience",
]:
    setattr(post_parser_module, name, lambda *args, **kwargs: "")
post_parser_module.llm_extract = lambda *args, **kwargs: {}
post_parser_module.extract_emails = lambda *args, **kwargs: ""
post_parser_module.score_domain_relevance = lambda *args, **kwargs: "Low"
post_parser_module.is_good_fit = lambda *args, **kwargs: (True, "")
post_parser_module.DOMAIN_KEYWORDS = []
sys.modules.setdefault("post_parser", post_parser_module)

from scrapers.web_scrapers import _extract_naukri_jobs_from_scrapling  # noqa: E402


class FakeElement:
    def __init__(self, text="", attrs=None, selectors=None):
        self._text = text
        self.attrib = attrs or {}
        self._selectors = selectors or {}

    def css(self, selector):
        return self._selectors.get(selector, [])

    def get_all_text(self, strip=False):
        return self._text.strip() if strip else self._text


class NaukriScraplingParserTests(unittest.TestCase):
    def test_extracts_jobs_and_deduplicates_by_url(self):
        first = FakeElement(selectors={
            "a.title": [FakeElement("Senior AI Engineer", {"href": "https://www.naukri.com/job-1"})],
            "a.comp-name": [FakeElement("Health AI Labs")],
            ".locWdth": [FakeElement("Bengaluru")],
            ".expwdth": [FakeElement("2-5 Yrs")],
            ".sal": [FakeElement("15-30 Lacs PA")],
            ".tag-li, .dot-gt .tag-li, .tags-gt span": [
                FakeElement("Python"),
                FakeElement("Machine Learning"),
            ],
        })
        duplicate = FakeElement(selectors={
            "a.title": [FakeElement("Senior AI Engineer", {"href": "https://www.naukri.com/job-1"})],
        })
        page = FakeElement(selectors={".srp-jobtuple-wrapper": [first, duplicate]})

        jobs = _extract_naukri_jobs_from_scrapling(page)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Senior AI Engineer")
        self.assertEqual(jobs[0]["company"], "Health AI Labs")
        self.assertEqual(jobs[0]["location"], "Bengaluru")
        self.assertEqual(jobs[0]["jobUrl"], "https://www.naukri.com/job-1")
        self.assertIn("Experience: 2-5 Yrs.", jobs[0]["desc"])
        self.assertIn("Salary: 15-30 Lacs PA.", jobs[0]["desc"])
        self.assertIn("Skills: Python, Machine Learning", jobs[0]["desc"])

    def test_skips_cards_without_title_or_url(self):
        missing_url = FakeElement(selectors={"a.title": [FakeElement("AI Engineer")]})
        missing_title = FakeElement(selectors={"a.title": [FakeElement("", {"href": "https://www.naukri.com/job-2"})]})
        page = FakeElement(selectors={".srp-jobtuple-wrapper": [missing_url, missing_title]})

        self.assertEqual(_extract_naukri_jobs_from_scrapling(page), [])


if __name__ == "__main__":
    unittest.main()
