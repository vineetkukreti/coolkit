#!/usr/bin/env python3
"""
Apply all fixes to config_sources.py based on DOM inspection results.
- Updates selectors for detected sites
- Fixes URLs for failed sites
- Replaces dead sites with alternatives
"""

import os, sys, json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Load inspection results
with open("data/dom_inspection.json") as f:
    inspection = json.load(f)

from config_sources import GENERIC_HTML_SOURCES

# ─── FIXES ────────────────────────────────────────────────────────────────────

# 1. Selector updates from auto-detection
SELECTOR_FIXES = {
    "tokyodev": {
        "urls": ["https://www.tokyodev.com/jobs?fully_remote=true"],
        "selectors": {"card": "div.relative", "title": "h4 a", "company": "[class*='company']", "location": "[class*='loc']", "link": "a[href*='job']"},
    },
    "nodesk": {
        "selectors": {"card": "div.flex", "title": "h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "workinstartups": {
        "selectors": {"card": "[class*='job']", "title": "h2 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "aijobs": {
        "selectors": {"card": "li.d-flex", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "gaijinpot": {
        "urls": ["https://jobs.gaijinpot.com/index/index/search/1?keyword=engineer&category_id=32"],
        "selectors": {"card": "li", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "aimljobs": {
        "selectors": {"card": "[class*='job']", "title": "h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "eudatajobs": {
        "selectors": {"card": "a.job", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "foundit": {
        "selectors": {"card": "div.accordion-header", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='career']"},
    },
    "cryptojobslist": {
        "selectors": {"card": "div.flex", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='loc']", "link": "a[href*='job']"},
    },
    "berlinstartupjobs": {
        "selectors": {"card": "[class*='job']", "title": "h3", "company": "[class*='company']", "location": "[class*='place']", "link": "a[href*='job']"},
    },
    "builtin": {
        "selectors": {"card": "[class*='job']", "title": "h2 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "cryptojobs": {
        "selectors": {"card": "[class*='job']", "title": "h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "academicjobs": {
        "selectors": {"card": "li", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "remoterocketship": {
        "selectors": {"card": "h3.text-lg", "title": "h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h3 a"},
    },
    "remote3": {
        "selectors": {"card": "[class*='job']", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "hnhiring": {
        "urls": ["https://hnhiring.com/locations/remote"],
        "selectors": {"card": "p", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "web3career": {
        "selectors": {"card": "[class*='job']", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "relocateme": {
        "selectors": {"card": "[class*='result']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "remotifyeurope": {
        "selectors": {"card": "div.relative", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "nofluffjobs": {
        "selectors": {"card": "div.list-container", "title": "h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "landingjobs": {
        "selectors": {"card": "[class*='job']", "title": "h2 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "jobstreetsg": {
        "selectors": {"card": "article, [data-search-sol-meta]", "title": "h3 a, a[data-automation='jobTitle']", "company": "[data-automation='jobCompany'], [class*='company']", "location": "[data-automation='jobLocation'], [class*='location']", "link": "h3 a"},
    },
    "internshala": {
        "selectors": {"card": "[class*='card']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "qureos": {
        "selectors": {"card": "[class*='card']", "title": "div[class*='title']", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "naturecareers": {
        "selectors": {"card": "[class*='job']", "title": "h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h3 a"},
    },
    "datajobs": {
        "selectors": {"card": "[class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "governmentjobs": {
        "selectors": {"card": "tr", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "jobsdbsg": {
        "selectors": {"card": "[class*='result']", "title": "h2 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "talent": {
        "selectors": {"card": "article", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "iqvia": {
        "selectors": {"card": "[class*='job']", "title": "h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
    "monster": {
        "urls": ["https://www.monster.com/jobs/search?q=AI+Engineer&where=remote"],
        "selectors": {"card": "[class*='card']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "kdnuggets": {
        "selectors": {"card": "li", "title": "a", "company": "span", "location": "span", "link": "a[href]"},
    },
    "ikigai": {
        "selectors": {"card": "ul.wp-block-list", "title": "a", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href]"},
    },
}

# 2. URL fixes for failed sites
URL_FIXES = {
    "eurotechjobs": {"urls": ["https://www.eurotechjobs.com/jobs?q=AI+engineer"]},
    "hirist": {"urls": ["https://www.hirist.tech/j?q=AI+engineer"]},
    "iimjobs": {"urls": ["https://www.iimjobs.com/search?q=AI+engineer"]},
    "daijob": {"urls": ["https://www.daijob.com/en/jobs"]},
    "naukrigulf": {"urls": ["https://www.naukrigulf.com/ai-engineer-jobs-in-uae"]},
    "remoteco": {"urls": ["https://remote.co/remote-jobs/developer/"]},
    "careersgovsg": {"urls": ["https://careers.pageuppeople.com/688/cwlive/en/listing/"]},
}

# 3. Replacements for dead/permanently-broken sites
REPLACEMENTS = {
    # Dead sites → replace with working alternatives
    "timesjobs": {
        "label": "Shine.com",
        "group": "india",
        "urls": ["https://www.shine.com/job-search/ai-engineer-jobs"],
        "selectors": {"card": "[class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://www.shine.com",
    },
    "pallet": {
        "label": "Otta Jobs",
        "group": "niche",
        "urls": ["https://app.otta.com/jobs"],
        "selectors": {"card": "article, [class*='job']", "title": "h3, h2", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://app.otta.com",
    },
    "aijoboard": {
        "label": "AI Career Hub",
        "group": "ai_ml",
        "urls": ["https://aicareerhub.com/jobs?q=AI+engineer"],
        "selectors": {"card": "[class*='job'], article", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://aicareerhub.com",
    },
    "workhap": {
        "label": "JustRemote",
        "group": "europe",
        "urls": ["https://justremote.co/remote-developer-jobs?search=AI"],
        "selectors": {"card": "article, [class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://justremote.co",
    },
    "techhiringsg": {
        "label": "NodeFlair SG",
        "group": "singapore",
        "urls": ["https://nodeflair.com/jobs?query=AI+engineer&sort_by=recent"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://nodeflair.com",
    },
    "mljobs": {
        "label": "ML Jobs Board",
        "group": "ai_ml",
        "urls": ["https://mljobsboard.com/jobs"],
        "selectors": {"card": "[class*='job'], article", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://mljobsboard.com",
    },
    # Blocked sites → replace with working alternatives
    "startupjobs": {
        "label": "Startup Jobs",
        "group": "startup",
        "urls": ["https://www.startupers.com/jobs?q=AI+engineer"],
        "selectors": {"card": "[class*='job'], article", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://www.startupers.com",
    },
    "f6s": {
        "label": "F6S Jobs",
        "group": "startup",
        "urls": ["https://www.f6s.com/jobs?q=AI+engineer"],
        "selectors": {"card": "[class*='job'], article", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://www.f6s.com",
    },
    "remoteineurope": {
        "label": "Europe Remotely",
        "group": "europe",
        "urls": ["https://europeremotely.com/engineering/"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://europeremotely.com",
    },
    "gulftalent": {
        "label": "Gulf Talent",
        "group": "uae",
        "urls": ["https://www.gulftalent.com/uae/jobs/artificial-intelligence"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://www.gulftalent.com",
    },
    "irishjobs": {
        "label": "Jobs.ie",
        "group": "europe",
        "urls": ["https://www.jobs.ie/AI-Engineer-Jobs/"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://www.jobs.ie",
    },
    "researchgate": {
        "label": "ScholarshipDB Research",
        "group": "academic",
        "urls": ["https://scholarshipdb.net/scholarships?q=artificial+intelligence"],
        "selectors": {"card": "[class*='result'], article", "title": "h2 a, h3 a", "company": "[class*='university']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://scholarshipdb.net",
    },
    "jobgether": {
        "label": "Jobgether",
        "group": "remote",
        "urls": ["https://jobgether.com/search-ai-engineer-remote"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://jobgether.com",
    },
    "simplyhired": {
        "label": "SimplyHired",
        "group": "us",
        "urls": ["https://www.simplyhired.com/search?q=AI+engineer&l=remote"],
        "selectors": {"card": "article, [class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
        "base_url": "https://www.simplyhired.com",
    },
    "jooble": {
        "label": "Jooble",
        "group": "remote",
        "urls": ["https://jooble.org/SearchResult?date=3&rgns=Remote&ukw=AI+engineer"],
        "selectors": {"card": "[class*='vacancy'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://jooble.org",
    },
    "lensa": {
        "label": "Lensa",
        "group": "us",
        "urls": ["https://lensa.com/ai-engineer-jobs/remote"],
        "selectors": {"card": "article, [class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
        "base_url": "https://lensa.com",
    },
    "ziprecruiter": {
        "label": "ZipRecruiter",
        "group": "us",
        "urls": ["https://www.ziprecruiter.com/jobs-search?search=AI+Engineer&location=Remote"],
        "selectors": {"card": "article, [class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
        "base_url": "https://www.ziprecruiter.com",
    },
    "remotiveeurope": {
        "label": "Remotive Europe",
        "group": "europe",
        "urls": ["https://remotive.com/remote-jobs/software-dev?location=europe"],
        "selectors": {"card": "article, [class*='job']", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
        "base_url": "https://remotive.com",
    },
    "contra": {
        "label": "Contra",
        "group": "freelance",
        "urls": ["https://contra.com/discover?q=AI+engineer"],
        "selectors": {"card": "article, [class*='card']", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='opportunity']"},
        "base_url": "https://contra.com",
    },
    # Sites that need different approaches
    "swissdevjobs": {
        "label": "SwissDevJobs",
        "group": "europe",
        "urls": ["https://swissdevjobs.ch/"],
        "selectors": {"card": "[class*='job'], article", "title": "h2, h3", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://swissdevjobs.ch",
    },
    "mycareersfuture": {
        "label": "MyCareersFuture SG",
        "group": "singapore",
        "urls": ["https://www.mycareersfuture.gov.sg/search?search=AI+engineer&sortBy=new_posting_date"],
        "selectors": {"card": "[class*='card'], article", "title": "h2 a, h3 a, span[class*='title']", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
        "base_url": "https://www.mycareersfuture.gov.sg",
    },
    "workable": {
        "label": "Workable",
        "group": "ats",
        "urls": ["https://apply.workable.com/search/?query=AI+engineer&location=remote"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
        "base_url": "https://apply.workable.com",
    },
    # No-jobs sites → fix URLs or selectors
    "remote4me": {
        "urls": ["https://remote4me.com/?search=AI"],
        "selectors": {"card": "[class*='job'], article, div.row", "title": "h2 a, h3 a, a", "company": "[class*='company'], span", "location": "[class*='location'], span", "link": "a[href]"},
    },
    "healthecareers": {
        "urls": ["https://www.healthecareers.com/jobs/ai-engineer"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "dubizzle": {
        "urls": ["https://www.dubizzle.com/jobs/it-software-development/?keyword=AI+engineer"],
        "selectors": {"card": "[class*='listing'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
    },
    "welcomejungle": {
        "urls": ["https://www.welcometothejungle.com/en/jobs?query=AI+engineer&refinementList%5Bremote%5D%5B%5D=fulltime"],
        "selectors": {"card": "[class*='card'], article", "title": "h3, h4, [class*='title']", "company": "[class*='company']", "location": "[class*='location']", "link": "a[href*='job']"},
    },
    "ukcivilservice": {
        "urls": ["https://www.civilservicejobs.service.gov.uk/csr/jobs.cgi?jcode=0&q=AI+engineer"],
        "selectors": {"card": "[class*='result'], article", "title": "h3 a, h2 a", "company": "[class*='department']", "location": "[class*='location']", "link": "h3 a, h2 a"},
    },
    "careerjet": {
        "urls": ["https://www.careerjet.com/search/jobs?s=AI+engineer&l=remote&sort=date"],
        "selectors": {"card": "[class*='job'], article", "title": "h2 a, h3 a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a, h3 a"},
    },
    "adzuna": {
        "urls": ["https://www.adzuna.com/search?q=AI+engineer&w=remote"],
        "selectors": {"card": "[class*='result'], article", "title": "h2 a, [class*='title'] a", "company": "[class*='company']", "location": "[class*='location']", "link": "h2 a"},
    },
    "dice": {
        "urls": ["https://www.dice.com/jobs?q=AI+Engineer&location=Remote&countryCode=US&radius=30&radiusUnit=mi&page=1&pageSize=40&language=en"],
        "selectors": {"card": "[data-cy='search-card'], [class*='card']", "title": "[data-cy='card-title'] a, h5 a", "company": "[data-cy='search-result-company-name']", "location": "[data-cy='search-result-location']", "link": "[data-cy='card-title'] a, h5 a"},
    },
}

# Apply all fixes
applied = 0
for key, fixes in {**SELECTOR_FIXES, **URL_FIXES, **REPLACEMENTS}.items():
    if key in GENERIC_HTML_SOURCES:
        for field, value in fixes.items():
            if field in ("selectors", "urls", "label", "group", "base_url"):
                GENERIC_HTML_SOURCES[key][field] = value
                applied += 1

print(f"Applied {applied} fixes to {len(SELECTOR_FIXES) + len(URL_FIXES) + len(REPLACEMENTS)} sources")
print(f"Total HTML sources: {len(GENERIC_HTML_SOURCES)}")

# Write back — we'll generate a clean version of the GENERIC_HTML_SOURCES dict
output_lines = []
for key, config in GENERIC_HTML_SOURCES.items():
    sel = config.get("selectors", {})
    output_lines.append(f'    "{key}": {{')
    output_lines.append(f'        "label": "{config.get("label", key)}",')
    output_lines.append(f'        "group": "{config.get("group", "other")}",')
    urls = config.get("urls", [])
    output_lines.append(f'        "urls": {json.dumps(urls)},')
    output_lines.append(f'        "selectors": {{')
    output_lines.append(f'            "card": "{sel.get("card", "article")}",')
    output_lines.append(f'            "title": "{sel.get("title", "h2 a")}",')
    output_lines.append(f'            "company": "{sel.get("company", "[class*=\'company\']")}",')
    output_lines.append(f'            "location": "{sel.get("location", "[class*=\'location\']")}",')
    output_lines.append(f'            "link": "{sel.get("link", "a[href]")}",')
    output_lines.append(f'        }},')
    output_lines.append(f'        "base_url": "{config.get("base_url", "")}",')
    output_lines.append(f'    }},')

print(f"\nGenerated {len(output_lines)} lines of updated config")
print(f"Saving to data/fixed_sources.py...")

with open("data/fixed_sources.py", "w") as f:
    f.write("# Auto-generated fixed selectors\nGENERIC_HTML_SOURCES_FIXED = {\n")
    f.write("\n".join(output_lines))
    f.write("\n}\n")

print("Done! Review data/fixed_sources.py then apply to config_sources.py")
