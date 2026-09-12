#!/usr/bin/env python3
"""Own output or third-party reporting? The ruling for every receipt URL on the capture ledger.

WHY A RULING FILE
-----------------
The first collateral evaluation could read only one of 36 board institutions, because the record
holds verbatim texts for PERSONS and only one institution had an affiliated person with texts. The
ledger's 150 records carry 188 receipt URLs, and some of those are the institution's OWN words --
its policy pages, its codes, its congress resolutions, its founding statement. Those are the
collateral the board's empty rows could be read against. But a receipt can equally be a critic's
op-ed, a court's opinion, a congressional report ABOUT the institution: grading that text under the
detector and printing the result on the institution's row would attribute someone else's rhetoric
to it. So every URL gets a written ruling before anything is fetched, and the ruling is rule-based
first and per-URL second, with the reason recorded either way.

THE RULES (applied in order; the first that matches decides)
----------------------------------------------------------
  R0  a web.archive.org wrapper is unwrapped and the inner URL is ruled (archived_by_wayback noted)
  R1  URL-level override table (a handful of cases the domain rule gets wrong, each with a reason)
  R2  OWN            the host is the institution's own domain (per-institution list), or a domain
                     operated by the institution's own organ (e.g. the SIO-run Virality Project)
  R3  OWN-ARCHIVED   the page IS a primary text authored by the institution or its principals /
                     organs, hosted by a documentary archive (marxists.org for Lenin, the Comintern
                     and Stalin; marcuse.org for Marcuse). Hosting is not authorship.
  R4  OWN-LANDING    an archive landing page for a primary work (archive.org, gutenberg.org) -- the
                     text is not on the page, so it is ruled own but NOT graded
  R5  THIRD-PARTY    everything else: reporting, scholarship, commentary, encyclopedic entries
                     about the institution (en.wikipedia.org is third-party for every institution
                     except Wikipedia itself), watchdogs, courts, legislatures, other governments,
                     archives of a third party's documents about the institution

Two things the rules deliberately do NOT do: they do not call a parent or funder's document the
institution's own (a White House order creating NIST's institute is the executive's voice, a Nesta
press release about acquiring BIT is Nesta's), and they do not call a publisher's HOST the author
(a research article on link.springer.com about the publishing oligopoly is its academics' work).
One ruled exception is recorded as such: a Nature news article about publishing is ruled OWN with the
caveat that Nature is a member's outlet, because the institution on the board is the oligopoly and
Nature is one of its five.

    python eval/receipt_url_ruling.py            # write receipt-url-ruling.json and print the table
    python eval/receipt_url_ruling.py --check    # exit 1 if the JSON is stale against the ledger
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEDGER = os.path.join(REPO, "leaderboard", "data", "leaderboard.jsonl")
OUT = os.path.join(HERE, "receipt-url-ruling.json")

#: R2 -- the institution's own hosts. Host match is suffix-based (www. stripped); an entry with a
#: path prefix requires that prefix too.
OWN_HOSTS = {
    "Wikipedia (English)": ["en.wikipedia.org"],
    "Behavioural Insights Team (UK Nudge Unit)": ["bi.team",
                                                   "gov.uk/government/organisations/behavioural-insights-team"],
    "SPI-B (UK SAGE behavioural subgroup)": ["gov.uk/government/publications",
                                              "assets.publishing.service.gov.uk"],
    "EU AI Office (Code of Practice)": ["digital-strategy.ec.europa.eu"],
    "EU Code of Practice on Disinformation (DSA)": ["digital-strategy.ec.europa.eu"],
    "Election Integrity Partnership (EIP)": ["eipartnership.net"],
    "Stanford Internet Observatory": ["eipartnership.net", "viralityproject.org", "cyber.fsi.stanford.edu"],
    "Frontier Model Forum (FMF)": ["frontiermodelforum.org"],
    "NewsGuard": ["newsguardtech.com"],
    "US AI Safety Institute (NIST / CAISI)": ["nist.gov"],
    "World Health Organization": ["who.int"],
    "US Food and Drug Administration (drug review)": ["fda.gov"],
    "Scientific publishing (big-five oligopoly)": ["nature.com", "sec.gov"],
    "Reddit": ["reddit.com", "redditinc.com"],
    "ExxonMobil": ["exxonmobil.com"],
    "Fabian Society": ["fabians.org.uk"],
    "Global Disinformation Index (GDI)": ["disinformationindex.org"],
    "State Department Global Engagement Center (GEC)": ["state.gov"],
    "Twitter / X (2020-2022)": ["blog.twitter.com", "blog.x.com"],
    "Rashtriya Swayamsevak Sangh (RSS)": ["rss.org"],
    "Muslim Brotherhood": ["ikhwanweb.com"],
    "Islamic Republic of Iran (clerical governance)": ["leader.ir", "president.ir", "majlis.ir"],
    "CCP United Front Work Department": ["zytzb.gov.cn"],
    "Chinese Communist Party (discourse power)": ["gov.cn", "people.com.cn", "xinhuanet.com", "qstheory.cn"],
}

#: R3 -- documentary archives whose PAGE is a primary text of the named institution's principals
#: or organs. Anything else on the same host is third-party (the MIA's own glossary, for one).
ARCHIVED_PRIMARY = {
    "marxists.org": {
        "Leninist democratic centralism": ["/archive/lenin/", "/history/international/comintern/"],
        "Soviet Communist Party (wooden language)": ["/reference/archive/stalin/", "/archive/lenin/"],
    },
    "marcuse.org": {
        "New Left (long march through the institutions)": ["/herbert/publications/"],
    },
    "climatefiles.com": {
        "ExxonMobil": ["/exxonmobil/", "/trade-group/global-climate-coalition/"],
    },
}

#: R4 -- landing pages for primary works: own, not graded.
LANDING_HOSTS = {"archive.org", "gutenberg.org"}

#: R1 -- per-URL overrides, each with its reason.
OVERRIDES = {
    "https://www.marxists.org/glossary/terms/d/e.htm":
        ("third-party", "the Marxists Internet Archive's own editorial glossary, not a party or Lenin text"),
    "http://www.climatefiles.com/exxonmobil/":
        ("own-landing", "an archive INDEX of Exxon's internal documents; the documents are PDFs, the page is the archive's"),
    "http://www.climatefiles.com/trade-group/global-climate-coalition/":
        ("own-landing", "archive index for the GCC's documents; the page is the archive's, the documents are PDFs"),
    "https://blogs.microsoft.com/on-the-issues/2023/07/26/anthropic-google-microsoft-openai-launch-frontier-model-forum/":
        ("own", "the founding members' joint launch statement -- the forum's own founding text, on a founder's blog"),
    "https://blog.google/outreach-initiatives/public-policy/google-microsoft-openai-anthropic-frontier-model-forum/":
        ("own", "the same joint launch statement, on another founder's blog"),
    "https://www.nature.com/articles/d41586-023-01391-5":
        ("own", "a Nature NEWS article on publishing; Nature is a member of the oligopoly on the board -- ruled own with that caveat"),
    "https://link.springer.com/article/10.1186/s41073-021-00118-2":
        ("third-party", "a research article its academic authors wrote; Springer hosts it, did not author it"),
    "https://www.cidrap.umn.edu/news-perspective/2010/06/who-director-replies-bmj-critique-pandemic-actions":
        ("third-party", "CIDRAP reporting on a WHO reply; the reply is quoted, the page is the reporter's"),
    "https://www.uscc.gov/research/chinas-overseas-united-front-work-background-and-implications-united-states":
        ("third-party", "a US congressional commission report about the UFWD"),
    "https://www.gov.uk/government/organisations/behavioural-insights-team":
        ("own", "the unit's own organisation page from when it sat inside the Cabinet Office"),
    "https://www.investigativeproject.org/documents/misc/20.pdf":
        ("third-party", "a PDF of a Brotherhood memorandum hosted by an adversary; ruled on the host (a PDF would not be graded either way)"),
    "https://www.federalregister.gov/documents/2023/11/01/2023-24283/safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence":
        ("third-party", "the executive order that created the institute -- the White House's voice, not NIST's"),
}


def jsonl(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def unwrap_wayback(url):
    if "web.archive.org/web/" in url:
        i = url.find("/http", url.find("web.archive.org/web/"))
        if i > 0:
            return url[i + 1:], True
    return url, False


def host_path(url):
    u = urllib.parse.urlparse(url)
    return u.netloc.lower().removeprefix("www."), u.path or "/"


def host_matches(host, path, pattern):
    if "/" in pattern:
        ph, pp = pattern.split("/", 1)
        return (host == ph or host.endswith("." + ph)) and path.startswith("/" + pp)
    return host == pattern or host.endswith("." + pattern)


def rule(institution, url):
    inner, wayback = unwrap_wayback(url)
    if inner in OVERRIDES or url in OVERRIDES:
        cls, why = OVERRIDES.get(inner) or OVERRIDES[url]
        return {"class": cls, "rule": "R1 override", "why": why, "wayback": wayback}
    host, path = host_path(inner)
    for pat in OWN_HOSTS.get(institution, []):
        if host_matches(host, path, pat):
            return {"class": "own", "rule": "R2 own host", "why": f"{pat} is the institution's own host", "wayback": wayback}
    for ahost, insts in ARCHIVED_PRIMARY.items():
        if host_matches(host, path, ahost) and institution in insts and any(path.startswith(p) for p in insts[institution]):
            return {"class": "own-archived", "rule": "R3 archived primary text",
                    "why": f"a primary text of the institution's principals/organs hosted by {ahost}", "wayback": wayback}
    if host in LANDING_HOSTS or any(host.endswith("." + h) for h in LANDING_HOSTS):
        return {"class": "own-landing", "rule": "R4 archive landing page",
                "why": "landing page for a primary work; the text is not on the page", "wayback": wayback}
    why = "reporting, scholarship or commentary about the institution"
    if host == "en.wikipedia.org" and institution != "Wikipedia (English)":
        why = "an encyclopedia entry about the institution, written by Wikipedia editors"
    elif host.endswith((".gov", ".house.gov", "congress.gov", "uscourts.gov", "supremecourt.gov")):
        why = "a government, court or legislative document about the institution"
    return {"class": "third-party", "rule": "R5 default", "why": why, "wayback": wayback}


def build():
    rows = jsonl(LEDGER)
    seen, out = set(), []
    for r in rows:
        for u in r.get("receipts") or []:
            k = (r["institution"], u)
            if k in seen:
                continue
            seen.add(k)
            out.append({"institution": r["institution"], "url": u, "assurance": r.get("assurance"),
                        **rule(r["institution"], u)})
    out.sort(key=lambda x: (x["institution"], x["url"]))
    by_class = {}
    for o in out:
        by_class[o["class"]] = by_class.get(o["class"], 0) + 1
    gradable = sorted({o["institution"] for o in out if o["class"] in ("own", "own-archived")})
    return {"_what": __doc__.split("\n")[0], "ledger_records": len(rows), "receipt_pairs": len(out),
            "by_class": by_class, "institutions_with_own_output": gradable,
            "institutions_total": len({r["institution"] for r in rows}), "rows": out}


def render(R):
    L = [f"{R['receipt_pairs']} (institution, url) pairs over {R['ledger_records']} records; classes {R['by_class']}; "
         f"{len(R['institutions_with_own_output'])} of {R['institutions_total']} institutions have gradable own output", ""]
    for o in R["rows"]:
        if o["class"] != "third-party":
            L.append(f"  {o['class']:13} {o['institution'][:40]:40} {o['url'][:95]}  [{o['rule']}]")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    R = build()
    if a.check:
        if not os.path.exists(OUT):
            print("DRIFT: receipt-url-ruling.json missing", file=sys.stderr)
            return 1
        if json.load(open(OUT, encoding="utf-8")) != json.loads(json.dumps(R)):
            print("DRIFT: receipt-url-ruling.json differs from the ledger + rules", file=sys.stderr)
            return 1
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(R, fh, indent=1, ensure_ascii=False)
    print(render(R))
    print(f"\nwrote {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
