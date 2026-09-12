#!/usr/bin/env python3
"""Fetch a bounded control corpus of AI-governance / AI-safety institutional shop-talk.

WHY THIS SOURCE
---------------
`RESULTS-2026-09-07-cue-repair.md` ran a pre-registered cut rule over 17 candidate cues and kept
13, seven of them (`training pipeline`, `diffuse`, `arithmetic`, `proprietary model`, `a few
hundred`, `high score`, `in a bid to`) because they occur ZERO times in either background pool the
rule is measured against -- the unannotated PTC news background and the general-prose pool (Federal
Register notices, congressional hearings, public rulemaking comments). None of those documents are
written by people doing AI safety or governance work, so a cue that is ordinary trade vocabulary in
THAT register has no chance to be recognised as such. `PREREG-2026-09-08-shoptalk-corpus.md`
pre-registers this corpus and the rule it will be measured against; this fetcher builds it.

SOURCE CLASSES (see the pre-registration for the full rationale)
------------------------------------------------------------------
1. AI-lab safety/policy blog posts -- Anthropic, DeepMind, Frontier Model Forum, METR, Apollo
   Research, Redwood Research. Direct URL fetch.
2. Governance think-tank pieces -- GovAI (Centre for the Governance of AI). Direct URL fetch.
3. Standards/framework text -- NIST AI RMF, NIST AISI, UK AISI, the Bletchley Declaration, the
   Seoul frontier AI safety commitments, the Hiroshima AI Process code of conduct, EO 14110's
   Federal Register summary. Direct URL fetch, all US/UK/EU government or international-process
   text.
4. Congressional-testimony-style policy prose -- govinfo.gov hearings on AI oversight, fetched
   through the SAME api.data.gov key and content path `fetch_govinfo.py` already uses, with a
   NEW term list scoped to AI governance and a NEW output file, so this corpus's provenance stays
   separate from the advocacy corpus fetched for a different register question.

SELECTION DISCIPLINE
---------------------
Every URL in DIRECT_URLS was chosen by TOPIC (a named institution's own safety/governance
publication) and verified to resolve BEFORE this file was written -- never by searching for a
candidate cue phrase, which is the selection-on-the-outcome trap `background_rate.py`'s own
docstring names and forbids. The govinfo terms are topic terms (AI oversight, frontier safety,
national security), matching how `fetch_govinfo.py` already works.

MAIN-CONTENT EXTRACTION IS APPROXIMATE, AND SAID SO
----------------------------------------------------
`<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<aside>` and `<form>` elements are
dropped before the text is pulled, but this is not a bespoke per-site scraper, so some residual
navigation or boilerplate text may remain in a handful of records. Every record's `text_extraction`
field says so. This matches the looseness already accepted elsewhere in this corpus (`_news-control`
carries fixed-size wire-copy chunks with no article boundary at all); a background bucket's job is
to measure how often a lens fires on prose NOT selected for the phenomenon, not to be a clean
literary edition.

DISCIPLINE
----------
Serial, one host at a time, a fixed delay, a descriptive User-Agent naming this research and a
contact address, no retries -- a failure stops the run rather than looping. A local on-disk cache
(`_html-cache/`) means a re-run never re-fetches a URL it already has.

    python corpus/fetch_ai_governance_shoptalk.py --dry-run
    python corpus/fetch_ai_governance_shoptalk.py                  # direct-URL pages only
    python corpus/fetch_ai_governance_shoptalk.py --govinfo         # + congressional hearings
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import textnorm  # noqa: E402

OUT = os.path.join(HERE, "ai-governance-shoptalk.jsonl")
CACHE_DIR = os.path.join(HERE, "_html-cache")
UA = "tradecraft-corpus-research/1.0 (bounded AI-governance control corpus; +https://github.com/gorrie/tradecraft)"
DELAY = 1.5

# ── source class 1-3: direct URLs, chosen by topic, verified live 2026-09-08 ──────────────────
#
# (source_class, org, title, author, date, url, note)
DIRECT_URLS = [
    ("lab-safety-blog", "Anthropic", "Anthropic's Responsible Scaling Policy", "Anthropic",
     "2023-09-19", "https://www.anthropic.com/news/anthropics-responsible-scaling-policy",
     "Frontier-lab policy shop-talk: capability thresholds, safety levels, scaling commitments."),
    ("lab-safety-blog", "Anthropic", "Core Views on AI Safety", "Anthropic", "2023-03-08",
     "https://www.anthropic.com/news/core-views-on-ai-safety",
     "Frontier-lab safety-research register: optimism/pessimism framing, research agendas."),
    ("lab-safety-blog", "Anthropic", "Responsible Scaling Policy (RSP)", "Anthropic", "2024-10-15",
     "https://www.anthropic.com/rsp",
     "The policy document itself, not a news writeup: thresholds, safeguards, governance."),
    ("lab-safety-blog", "Anthropic", "Reflections on our Responsible Scaling Policy", "Anthropic",
     "2024-05-08", "https://www.anthropic.com/news/reflections-on-our-responsible-scaling-policy",
     "Retrospective/self-critique register on the same policy."),
    ("lab-safety-blog", "Google DeepMind", "Introducing the Frontier Safety Framework",
     "Google DeepMind", "2024-05-17",
     "https://deepmind.google/discover/blog/introducing-the-frontier-safety-framework/",
     "Frontier-lab risk-framework announcement."),
    ("lab-safety-blog", "Google DeepMind", "Responsibility & Safety", "Google DeepMind", None,
     "https://deepmind.google/about/responsibility-safety/",
     "Institutional safety-practice overview page."),
    ("lab-safety-blog", "Google DeepMind", "Updating the Frontier Safety Framework",
     "Google DeepMind", "2025-02-04",
     "https://deepmind.google/discover/blog/updating-the-frontier-safety-framework/",
     "Framework revision announcement -- governance-process register."),
    ("lab-safety-blog", "Frontier Model Forum", "Announcing the Frontier Model Forum",
     "Frontier Model Forum", "2023-07-26",
     "https://www.frontiermodelforum.org/updates/announcing-the-frontier-model-forum/",
     "Industry-consortium founding announcement."),
    ("lab-safety-blog", "Frontier Model Forum",
     "FMF Announces First-of-its-Kind Information Sharing Agreement", "Frontier Model Forum", None,
     "https://www.frontiermodelforum.org/updates/fmf-announces-first-of-its-kind-information-sharing-agreement/",
     "Inter-institutional coordination announcement."),
    ("lab-safety-blog", "METR", "AI models are advancing fast -- can models be dangerous before public deployment?",
     "METR", "2025-01-17",
     "https://metr.org/blog/2025-01-17-ai-models-dangerous-before-public-deployment/",
     "Evaluation-org shop-talk: dangerous-capability thresholds."),
    ("lab-safety-blog", "METR", "It's good for AI to reason legibly and faithfully", "METR",
     "2025-03-11", "https://metr.org/blog/2025-03-11-good-for-ai-to-reason-legibly-and-faithfully/",
     "Evaluation methodology register."),
    ("lab-safety-blog", "METR", "Risk transparency", "METR", "2025-06-27",
     "https://metr.org/blog/2025-06-27-risk-transparency/",
     "Governance-process register: disclosure norms."),
    ("lab-safety-blog", "METR", "Common elements of frontier AI safety policies", "METR",
     "2025-12-09", "https://metr.org/blog/2025-12-09-common-elements-of-frontier-ai-safety-policies/",
     "Cross-lab policy comparison -- exactly the register that discusses thresholds/pipelines."),
    ("lab-safety-blog", "METR", "Sabotage risk report: Opus 4.6 review", "METR", "2026-03-12",
     "https://metr.org/blog/2026-03-12-sabotage-risk-report-opus-4-6-review/",
     "Model evaluation writeup register."),
    ("lab-safety-blog", "METR", "Red-teaming Anthropic's agent monitoring", "METR", "2026-03-25",
     "https://metr.org/blog/2026-03-25-red-teaming-anthropic-agent-monitoring/",
     "Red-team/evaluation register."),
    ("lab-safety-blog", "METR", "R&D section: Anthropic risk report (Feb 2026) review", "METR",
     "2026-05-08",
     "https://metr.org/blog/2026-05-08-rd-section-anthropic-risk-report-feb-2026-review/",
     "Model evaluation writeup register."),
    ("lab-safety-blog", "METR", "Investigating AI propensities after incidents", "METR",
     "2026-07-28", "https://metr.org/blog/2026-07-28-investigating-ai-propensities-after-incidents/",
     "Incident-investigation register."),
    ("lab-safety-blog", "METR", "METR's Responsible Scaling Policy engagement", "METR",
     "2023-09-26", "https://metr.org/blog/2023-09-26-rsp/",
     "Policy-engagement register."),
    ("lab-safety-blog", "METR", "Bounty for diverse, hard tasks for LLM agents", "METR",
     "2023-12-16", "https://metr.org/blog/2023-12-16-bounty-diverse-hard-tasks-for-llm-agents/",
     "Evaluation-infrastructure register (benchmark design, task pipelines)."),
    ("think-tank", "Centre for the Governance of AI (GovAI)",
     "A grading rubric for AI safety frameworks", "GovAI", None,
     "https://www.governance.ai/research-paper/a-grading-rubric-for-ai-safety-frameworks",
     "Governance-research register."),
    ("think-tank", "Centre for the Governance of AI (GovAI)",
     "Computing power and the governance of artificial intelligence", "GovAI", None,
     "https://www.governance.ai/research-paper/computing-power-and-the-governance-of-artificial-intelligence",
     "Compute-governance register."),
    ("think-tank", "Centre for the Governance of AI (GovAI)",
     "Assessing risk relative to competitors: an analysis of current AI company policies",
     "GovAI", None,
     "https://www.governance.ai/research-paper/assessing-risk-relative-to-competitors-an-analysis-of-current-ai-company-policies",
     "Cross-company policy comparison register."),
    ("think-tank", "Centre for the Governance of AI (GovAI)",
     "Coordinated pausing: an evaluation-based coordination scheme", "GovAI", None,
     "https://www.governance.ai/research-paper/coordinated-pausing-evaluation-based-scheme",
     "Governance-mechanism-design register."),
    ("think-tank", "Centre for the Governance of AI (GovAI)",
     "Economic policy challenges for the age of AI", "GovAI", None,
     "https://www.governance.ai/research-paper/economic-policy-challenges-for-the-age-of-ai",
     "Economic/labor-policy register (human capital, workforce)."),
    ("think-tank", "Centre for the Governance of AI (GovAI)", "The Brussels effect and AI",
     "GovAI", None, "https://www.governance.ai/research-paper/brussels-effect-ai",
     "International regulatory-competition register (level playing field)."),
    ("lab-safety-blog", "Apollo Research", "Theories of change for AI auditing",
     "Apollo Research", None,
     "https://www.apolloresearch.ai/blog/theories-of-change-for-ai-auditing",
     "Evaluation-org strategy register."),
    ("lab-safety-blog", "Apollo Research",
     "Our norms: conflicts of interest, security, science communication", "Apollo Research", None,
     "https://www.apolloresearch.ai/blog/our-norms-coi-security-science-communication",
     "Institutional-governance register."),
    ("lab-safety-blog", "Apollo Research", "Apollo Research: 18-month update", "Apollo Research",
     None, "https://www.apolloresearch.ai/blog/apollo-18-month-update",
     "Organizational-update register."),
    ("lab-safety-blog", "Redwood Research", "AI control", "Redwood Research", None,
     "https://www.redwoodresearch.org/research/ai-control",
     "Technical-safety-agenda register."),
    ("lab-safety-blog", "Redwood Research", "Hugging Face incident", "Redwood Research", None,
     "https://www.redwoodresearch.org/research/hugging-face-incident",
     "Incident-report register."),
    ("standards-framework", "NIST", "AI Risk Management Framework", "NIST", "2023-01-26",
     "https://www.nist.gov/itl/ai-risk-management-framework",
     "US government work, public domain. Standards-body register."),
    ("standards-framework", "NIST", "US AI Safety Institute (overview)", "NIST", None,
     "https://www.nist.gov/aisi",
     "US government work, public domain."),
    ("standards-framework", "UK AI Safety Institute", "AI Safety Institute (homepage)",
     "UK AISI", None, "https://www.aisi.gov.uk/",
     "UK Crown/government work."),
    ("standards-framework", "UK Government / AI Safety Summit",
     "The Bletchley Declaration", "Governments attending the AI Safety Summit", "2023-11-01",
     "https://www.gov.uk/government/publications/ai-safety-summit-2023-the-bletchley-declaration/the-bletchley-declaration-by-countries-attending-the-ai-safety-summit-1-2-november-2023",
     "Multilateral-declaration register."),
    ("standards-framework", "UK Government / AI Seoul Summit",
     "Frontier AI Safety Commitments, AI Seoul Summit 2024", "Governments and companies at the AI Seoul Summit",
     "2024-05-21",
     "https://www.gov.uk/government/publications/frontier-ai-safety-commitments-ai-seoul-summit-2024/frontier-ai-safety-commitments-ai-seoul-summit-2024",
     "Multilateral-commitment register."),
    ("standards-framework", "European Commission",
     "Hiroshima Process International Code of Conduct for Advanced AI Systems", "G7 / European Commission",
     "2023-10-30",
     "https://digital-strategy.ec.europa.eu/en/library/hiroshima-process-international-code-conduct-advanced-ai-systems",
     "International code-of-conduct register."),
    ("standards-framework", "Federal Register",
     "Safe, Secure, and Trustworthy Development and Use of Artificial Intelligence (EO 14110 summary)",
     "Executive Office of the President", "2023-11-01",
     "https://www.federalregister.gov/documents/2023/11/01/2023-24283/safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence",
     "US government work, public domain. Executive-order register."),
]

# ── source class 4: govinfo congressional hearings, same API + content path as fetch_govinfo.py,
#    a NEW term list and a NEW output file so provenance stays separate from the advocacy corpus.
GOVINFO_API = "https://api.govinfo.gov"
GOVINFO_KEY = os.environ.get("GOVINFO_API_KEY", "DEMO_KEY")
GOVINFO_TERMS = [
    "artificial intelligence risk management framework",
    "frontier artificial intelligence safety",
    "artificial intelligence national security oversight",
    "generative artificial intelligence regulation",
]
GOVINFO_PER_TERM = 4
GOVINFO_CAP = 16
GOVINFO_DELAY = 3.0
GOVINFO_CHARS = 30000
FRONT_MATTER_END = (
    "The Committee met", "The Subcommittee met", "The committee met", "The subcommittee met",
    "OPENING STATEMENT OF", "STATEMENT OF HON.", "PREPARED STATEMENT OF",
)


def _cache_path(url):
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return os.path.join(CACHE_DIR, h + ".html")


def fetch_html(url):
    """GET with the local cache. A cached copy is never re-fetched."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = _cache_path(url)
    if os.path.exists(cp):
        return io.open(cp, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as fh:
        html = fh.read().decode("utf-8", errors="replace")
    io.open(cp, "w", encoding="utf-8", newline="\n").write(html)
    return html


def extract_main_text(html):
    """Best-effort main content: drop non-prose chrome, then the shared normaliser.

    Not a bespoke per-site scraper -- see the module docstring. Returns (text, method).
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form",
                         "noscript", "svg", "button"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        text = " ".join(text.split())
        return text, "bs4-chrome-stripped"
    except ImportError:
        return textnorm.clean(html), "regex-tag-stripped (no bs4)"


def slug_id(source_class, url):
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return "%s_%s" % (source_class, h)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--govinfo", action="store_true", help="also fetch congressional hearings")
    args = ap.parse_args(argv)

    existing = set()
    if os.path.exists(OUT):
        for line in io.open(OUT, encoding="utf-8"):
            line = line.strip()
            if line:
                existing.add(json.loads(line)["id"])

    print("%d direct-URL document(s) planned (cache: %s)" % (len(DIRECT_URLS), CACHE_DIR))
    if args.dry_run:
        for sc, org, title, author, date, url, note in DIRECT_URLS:
            print("  [%s] %-28s %s" % (sc, org, title))
        if args.govinfo:
            print("govinfo terms: %s" % GOVINFO_TERMS)
        return 0

    written = 0
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as out:
        for sc, org, title, author, date, url, note in DIRECT_URLS:
            rid = slug_id(sc, url)
            if rid in existing:
                continue
            try:
                html = fetch_html(url)
            except Exception as exc:
                print("  fetch failed %s: %s -- stopping rather than retrying" % (url, str(exc)[:80]))
                break
            text, method = extract_main_text(html)
            if len(text.split()) < 100:
                print("  SKIP (too short after extraction, %d words): %s" % (len(text.split()), url))
                continue
            out.write(json.dumps({
                "id": rid,
                "source_class": sc,
                "register": "ai-governance-shoptalk",
                "org": org,
                "title": title,
                "author": author,
                "date": date,
                "source_url": url,
                "fetched": time.strftime("%Y-%m-%d"),
                "note": note,
                "text_extraction": method,
                "text": text,
            }, ensure_ascii=False) + "\n")
            written += 1
            print("  + %-28s %s" % (org, title))
            time.sleep(DELAY)

    if args.govinfo:
        written += fetch_govinfo_hearings(existing)

    print()
    print("wrote %d document(s) to %s" % (written, os.path.relpath(OUT, HERE)))
    print("Unlabelled by lens design -- topic-selected, never cue-selected.")
    return 0


def fetch_govinfo_hearings(existing):
    """Congressional hearings on AI oversight, via the govinfo API -- same discipline and content
    path as fetch_govinfo.py, a new term list, a new output file."""

    def search(term, limit):
        body = json.dumps({
            "query": "%s collection:(CHRG OR CREC)" % term,
            "pageSize": limit,
            "offsetMark": "*",
            "sorts": [{"field": "score", "sortOrder": "DESC"}],
        }).encode("utf-8")
        u = "%s/search?api_key=%s" % (GOVINFO_API, GOVINFO_KEY)
        req = urllib.request.Request(u, data=body,
                                     headers={"User-Agent": UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as fh:
            return json.loads(fh.read().decode("utf-8", errors="replace")).get("results", [])

    def fetch_content(package_id):
        u = "https://www.govinfo.gov/content/pkg/%s/html/%s.htm" % (package_id, package_id)
        req = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as fh:
            return fh.read().decode("utf-8", errors="replace")

    def body_window(body, chars):
        full_words = len(body.split())
        start = -1
        for marker in FRONT_MATTER_END:
            i = body.find(marker)
            if i >= 0 and (start < 0 or i < start):
                start = i
        if start < 0:
            return body[:chars], 0, len(body) > chars, full_words
        window = body[start:start + chars]
        if len(body) > start + chars:
            window = window.rsplit(" ", 1)[0]
            return window, start, True, full_words
        return window, start, False, full_words

    planned = []
    for term in GOVINFO_TERMS:
        try:
            hits = search(term, GOVINFO_PER_TERM)
        except Exception as exc:
            print("govinfo search failed for %r: %s -- stopping" % (term, str(exc)[:90]))
            break
        for h in hits:
            pid = h.get("packageId")
            rid = "gov_ai_%s" % pid if pid else None
            if not pid or rid in existing:
                continue
            planned.append((rid, term, h))
        time.sleep(GOVINFO_DELAY)

    seen, unique = set(), []
    for item in planned:
        if item[0] in seen:
            continue
        seen.add(item[0])
        unique.append(item)
    unique = unique[:GOVINFO_CAP]
    print("%d congressional hearing(s) to fetch (cap %d)" % (len(unique), GOVINFO_CAP))

    written = 0
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as out:
        for rid, term, h in unique:
            pid = h["packageId"]
            try:
                raw = fetch_content(pid)
            except Exception as exc:
                print("  govinfo fetch failed %s: %s -- stopping" % (rid, str(exc)[:70]))
                break
            body = textnorm.clean(raw)
            # CREC package ids returned by search do not all resolve through the CHRG content
            # path: 6 of 21 hits in the 2026-09-08 run came back as govinfo's "Page Not Found"
            # error shell (title "Skip to main content ... Search Page Not Found"), which is
            # real page content -- it fetches with HTTP 200 -- but is not the document. Caught
            # here rather than guessed-around, because guessing a corrected CREC path risks
            # silently writing a DIFFERENT real document under this package id.
            if "Search Page Not Found" in body or "The page you requeste" in body:
                print("  SKIP %s: govinfo content path returned its error shell, not the "
                      "document (known CREC gap)" % rid)
                continue
            body, skipped, was_cut, full_words = body_window(body, GOVINFO_CHARS)
            if len(body.split()) < 200:
                continue
            out.write(json.dumps({
                "id": rid,
                "source_class": "congressional-testimony",
                "register": "ai-governance-shoptalk",
                "org": "U.S. Congress",
                "title": h.get("title"),
                "author": None,
                "date": h.get("dateIssued"),
                "source_url": "https://www.govinfo.gov/app/details/%s" % pid,
                "fetched": time.strftime("%Y-%m-%d"),
                "found_by_term": term,
                "note": ("US government work, public domain. Congressional hearing: "
                         "AI-oversight testimony, fetched by TOPIC via the same govinfo "
                         "API/content path as fetch_govinfo.py, a separate term list and "
                         "output file so provenance stays distinct from the advocacy corpus."),
                "text_extraction": "govinfo-content-window (front-matter skipped, tail truncated)",
                "excerpt": True,
                "front_matter_chars_skipped": skipped,
                "truncated": was_cut,
                "truncated_at_chars": GOVINFO_CHARS if was_cut else None,
                "full_words": full_words,
                "text": body,
            }, ensure_ascii=False) + "\n")
            written += 1
            print("  + %-22s %s" % (rid, (h.get("title") or "")[:60]))
            time.sleep(GOVINFO_DELAY)
    return written


if __name__ == "__main__":
    sys.exit(main())
