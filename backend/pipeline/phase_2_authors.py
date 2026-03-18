"""Phase 2 — Notable-author evaluation and web-based hallucination verification.

For each unknown author in the citation batch, queries the LLM to determine
notability, then runs a 4-stage web verification pipeline to catch hallucinated
awards or fellowships:

1. Author homepage
2. Wikipedia (full article)
3. LLM-provided verification URL (sanitised)
4. Google Scholar search (fallback)
"""

import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests as _requests

from backend.core.config import logger, extract_json, coerce_llm_list_to_dict, handle_llm_error

# ---------------------------------------------------------------------------
# Web verification helpers
# ---------------------------------------------------------------------------


def _fetch_text(url: str, timeout: int = 5) -> str:
    """Fetch *url* and return stripped text content, or ``""`` on failure."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
            return re.sub(r"<[^<]+>", " ", html)
    except Exception:
        return ""


def _is_abbreviated_name(name: str) -> bool:
    """Return True if *name* looks like an abbreviated form (e.g. 'H. Seidel')."""
    parts = name.strip().split()
    if len(parts) < 2:
        return False
    # Check if the first part is a single letter or initial (e.g. 'H.' or 'H')
    first = parts[0].rstrip(".")
    return len(first) == 1 and first.isalpha()


def _get_surname(name: str) -> str:
    """Extract the surname (last part) from a name string."""
    parts = name.strip().split()
    return parts[-1] if parts else name


def verify_notable_claim(
    name: str,
    evidence: str,
    homepage: str,
    verification_keywords: list[str] | None = None,
    verification_url: str | None = None,
) -> tuple[bool, str, list[str]]:
    """Programmatic verification of LLM hallucination for notable authors.

    Cross-references claims against the author's homepage, Wikipedia, an
    LLM-provided verification URL, and Google Scholar search results.

    Returns ``(is_verified, evidence_string, scraped_urls)``.
    """
    if verification_keywords is None:
        verification_keywords = []

    text_corpus = ""
    scraped_urls: list[str] = []

    evidence_lower = evidence.lower()
    claims_in_evidence = [
        str(kw).lower()
        for kw in verification_keywords
        if str(kw).lower() in evidence_lower
    ]

    def _check_claims(corpus: str) -> bool:
        """Return True if any claimed keyword phrase is found in *corpus*.

        Uses word-level matching: all words in the keyword must appear
        somewhere in the corpus, but not necessarily as a contiguous
        substring.  This handles variations like "Fellow of the IEEE"
        matching the keyword ``"ieee fellow"``.
        """
        if not claims_in_evidence:
            return False
        corpus_lower = corpus.lower()
        for kw in claims_in_evidence:
            words = kw.split()
            if all(w in corpus_lower for w in words):
                return True
        return False

    # 1. Fetch Homepage (highest priority)
    if homepage and homepage.startswith("http"):
        scraped_urls.append(homepage)
        text = _fetch_text(homepage)
        if text.strip():
            text_corpus += text + " "
            if _check_claims(text_corpus):
                return True, evidence + " [AI Verified]", scraped_urls

    # 2. Fetch Wikipedia (full article, not just intro)
    def _fetch_wiki_extract(query_name: str) -> str:
        """Fetch Wikipedia extract for *query_name*, return text or ``""``."""
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&prop=extracts"
            f"&explaintext=1&titles={urllib.parse.quote(query_name)}&format=json"
        )
        scraped_urls.append(url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                for page in data.get("query", {}).get("pages", {}).values():
                    extract = page.get("extract", "")
                    if extract and page.get("pageid", -1) != -1:
                        return extract
        except Exception:
            pass
        return ""

    wiki_text = _fetch_wiki_extract(name)
    if not wiki_text and _is_abbreviated_name(name):
        # Try Wikipedia opensearch to resolve abbreviated name to full name
        surname = _get_surname(name)
        search_url = (
            "https://en.wikipedia.org/w/api.php?action=opensearch"
            f"&search={urllib.parse.quote(surname)}&limit=5&format=json"
        )
        scraped_urls.append(search_url)
        try:
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                results = json.loads(response.read())
                if isinstance(results, list) and len(results) >= 2:
                    for candidate_title in results[1]:
                        # Check if the surname matches
                        if surname.lower() in candidate_title.lower():
                            wiki_text = _fetch_wiki_extract(candidate_title)
                            if wiki_text:
                                break
        except Exception:
            pass
    if wiki_text:
        text_corpus += wiki_text + " "

    # If no claims to verify (LLM didn't output keywords), pass through
    if not claims_in_evidence:
        return True, evidence, scraped_urls

    # Check combined homepage + Wikipedia corpus
    if _check_claims(text_corpus):
        return True, evidence + " [AI Verified]", scraped_urls

    # 3. Fetch LLM-provided verification URL (sanitise compound strings)
    if verification_url and verification_url.startswith("http"):
        clean_url = re.split(r"[;\s]", verification_url)[0].rstrip(")")
        if clean_url.startswith("http"):
            scraped_urls.append(clean_url)
            vtext = _fetch_text(clean_url, timeout=5)
            if vtext.strip() and _check_claims(vtext):
                return True, evidence + " [AI Verified]", scraped_urls

    # 4. Google Scholar search as final fallback
    search_names = [name]
    if _is_abbreviated_name(name):
        # Also try with just the surname for abbreviated names
        search_names.append(_get_surname(name))

    for search_name in search_names:
        for kw in claims_in_evidence:
            query = f'"{search_name}" "{kw}"'
            search_url = (
                f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}&hl=en"
            )
            scraped_urls.append(search_url)
            try:
                resp = _requests.get(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=5,
                )
                if _check_claims(resp.text):
                    return True, evidence + " [AI Verified]", scraped_urls
            except Exception:
                pass

    # All sources failed — reject
    missing_claims = ", ".join(f"'{c}'" for c in claims_in_evidence)
    return (
        False,
        f"Failed verification: LLM claimed {missing_claims}, but these keywords were not found on scraped pages.",
        scraped_urls,
    )


# ---------------------------------------------------------------------------
# Main author-evaluation entry point
# ---------------------------------------------------------------------------


def evaluate_authors(
    client,
    model_name: str,
    eval_criteria: dict,
    collected_citations: list,
    target_id: str = None,
    system_user_id: int | None = None,
) -> None:
    """Query the LLM for author notability, then verify claims via the web."""
    from backend.database.sqlite_db import (
        get_author,
        upsert_author,
        update_citation_authors,
        get_target_status,
        update_target_progress,
    )

    unknown_authors = set()
    for citation in collected_citations:
        # Cap the number of authors evaluated per citation to save LLM tokens.
        # Only apply this cap to mega-collaborations (> 100 authors).
        authors = citation.get("authors", [])
        if len(authors) > 100:
            eval_authors = authors[:5] + authors[-2:]
        else:
            eval_authors = authors

        for author in eval_authors:
            name = author.get("name")
            if name and get_author(name) is None:
                unknown_authors.add(name)

    unknown_authors = list(unknown_authors)

    if not (unknown_authors and client):
        return

    logger.info(
        f"\nPhase 2: Querying Gemini for {len(unknown_authors)} unknown authors..."
    )
    chunk_size = 100

    for i in range(0, len(unknown_authors), chunk_size):
        if target_id and get_target_status(target_id) in ("paused", "cancelled"):
            logger.info(
                f"Target {target_id} paused or cancelled. Stopping author evaluation."
            )
            break

        chunk = unknown_authors[i : i + chunk_size]
        logger.info(
            f"  Batch {i // chunk_size + 1}/"
            f"{(len(unknown_authors) - 1) // chunk_size + 1} ({len(chunk)} authors)..."
        )

        prompt = (
            f"Criteria: {eval_criteria.get('notable_criteria')}\n\n"
            f"CRITICAL INSTRUCTION: Analyze the authors below. ONLY classify an author as notable "
            f"if there is STRONG, VERIFIABLE evidence matching the criteria. "
            f"DO NOT hallucinate awards or fellowships.\n\n"
            f"To save tokens, ONLY include authors in your JSON response if they ARE notable. "
            f"Omit all other authors.\n\n"
            f'For each notable author, respond with JSON: {{"name": {{"is_notable": true, "evidence": str, '
            f'"homepage": str, "verification_keywords": ["keyword1", "keyword2"], "verification_url": str}}}}.\n'
            f"Include 1-3 highly specific keywords in 'verification_keywords' "
            f"(e.g., 'fellow', 'nobel', 'award', 'best paper') to search for in their "
            f"Wikipedia/homepage to verify their evidence.\n"
            f"For 'verification_url', provide a SPECIFIC official URL where the claim can be verified "
            f"(e.g., the IEEE Fellow directory page, ACM Fellow list, or the conference awards page).\n\n"
            f"Authors:\n" + "\n".join(f"- {a}" for a in chunk)
        )

        for attempt in range(4):
            try:
                time.sleep(0.01)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "phase": "phase_2_author",
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "target_id": target_id,
                        "system_user_id": system_user_id,
                    },
                )
                parsed = extract_json(response.text)
                parsed = coerce_llm_list_to_dict(parsed, key_field="name", value_fields=("is_notable", "evidence"))

                # Parse all author data from the LLM response
                author_profiles = {}
                for author in chunk:
                    auth_data = parsed.get(author, {})
                    if isinstance(auth_data, dict):
                        is_notable = bool(auth_data.get("is_notable", False))
                        ev = str(auth_data.get("evidence", ""))
                        hp = str(auth_data.get("homepage", ""))
                        vkw = auth_data.get("verification_keywords", [])
                        if not isinstance(vkw, list):
                            vkw = []
                        vurl = str(auth_data.get("verification_url", ""))
                    else:
                        is_notable, ev, hp, vkw, vurl = False, "", "", [], ""

                    if hp and not hp.startswith("http"):
                        hp = ""

                    author_profiles[author] = {
                        "is_notable": is_notable,
                        "evidence": ev,
                        "homepage": hp,
                        "verification_keywords": vkw,
                        "verification_url": vurl,
                    }

                # Dispatch notable authors' web verification in parallel
                notables_to_verify = {
                    a: p for a, p in author_profiles.items() if p["is_notable"]
                }
                verification_results: dict = {}
                if notables_to_verify:
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_author = {
                            executor.submit(
                                verify_notable_claim,
                                a,
                                p["evidence"],
                                p["homepage"],
                                p["verification_keywords"],
                                p["verification_url"],
                            ): a
                            for a, p in notables_to_verify.items()
                        }
                        for future in as_completed(future_to_author):
                            a = future_to_author[future]
                            try:
                                verification_results[a] = future.result()
                            except Exception:
                                verification_results[a] = (
                                    False,
                                    author_profiles[a]["evidence"],
                                    [],
                                )

                # Collect verified and rejected authors from web verification
                verified_authors = {}
                rejected_authors = {}
                for author in chunk:
                    p = author_profiles[author]
                    if not p["is_notable"]:
                        continue
                    if author not in verification_results:
                        continue
                    is_ok, ev, scraped_urls = verification_results[author]
                    urls_str = ""
                    if scraped_urls:
                        urls_str = f" [Checked: {', '.join(scraped_urls)}]"
                    if is_ok:
                        verified_authors[author] = (ev, scraped_urls, urls_str)
                    else:
                        rejected_authors[author] = (ev, scraped_urls, urls_str, p)

                # --- Second-opinion LLM call for rejected authors ---
                if rejected_authors and client:
                    second_opinion_prompt = (
                        f"Criteria: {eval_criteria.get('notable_criteria')}\n\n"
                        f"The following authors were initially classified as notable, but "
                        f"automated web verification could NOT confirm their claims. "
                        f"For each author, I will tell you what was claimed and what "
                        f"verification was attempted.\n\n"
                        f"IMPORTANT: Web verification is imperfect — many legitimate authors "
                        f"fail verification because their pages are JavaScript-rendered, "
                        f"behind CAPTCHAs, use abbreviated names differently, or simply "
                        f"don't mention their awards prominently.\n\n"
                        f"For each author below, carefully reconsider: is this author "
                        f"GENUINELY notable by the criteria, or was the initial classification "
                        f"a hallucination? Respond with JSON:\n"
                        f'{{"author_name": {{"is_notable": true/false, "evidence": "why you believe this"}}}}\n\n'
                    )
                    for author, (ev, scraped_urls, urls_str, p) in rejected_authors.items():
                        kws = ", ".join(f"'{k}'" for k in p.get("verification_keywords", []))
                        checked = ", ".join(scraped_urls) if scraped_urls else "none"
                        second_opinion_prompt += (
                            f"- {author}\n"
                            f"  Initial claim: {p['evidence']}\n"
                            f"  Keywords searched: {kws}\n"
                            f"  Pages checked: {checked}\n"
                            f"  Result: keywords not found on any scraped page\n\n"
                        )

                    try:
                        time.sleep(0.01)
                        second_response = client.models.generate_content(
                            model=model_name,
                            contents=second_opinion_prompt,
                            config={
                                "phase": "phase_2_author_round_2",
                                "temperature": 0.1,
                                "top_p": 0.8,
                                "target_id": target_id,
                                "system_user_id": system_user_id,
                            },
                        )
                        second_parsed = extract_json(second_response.text)
                        second_parsed = coerce_llm_list_to_dict(
                            second_parsed, key_field="name",
                            value_fields=("is_notable", "evidence"),
                        )

                        for author, (ev, scraped_urls, urls_str, p) in rejected_authors.items():
                            second_data = second_parsed.get(author, {})
                            if isinstance(second_data, dict) and bool(second_data.get("is_notable", False)):
                                new_ev = str(second_data.get("evidence", p["evidence"]))
                                logger.info(
                                    f"    [NOTABLE - LLM 2nd opinion] {author} ({new_ev}){urls_str}"
                                )
                                verified_authors[author] = (
                                    new_ev + " [LLM Confirmed]",
                                    scraped_urls,
                                    urls_str,
                                )
                            else:
                                reason = str(second_data.get("evidence", ev)) if isinstance(second_data, dict) else ev
                                logger.info(
                                    f"    [REJECTED - CONFIRMED] {author} ({reason}){urls_str}"
                                )
                    except Exception:
                        # If second LLM call fails, keep all rejections as-is
                        for author, (ev, scraped_urls, urls_str, p) in rejected_authors.items():
                            logger.info(
                                f"    [REJECTED - HALLUCINATION] {author} ({ev}){urls_str}"
                            )

                # Log verified authors
                for author, (ev, scraped_urls, urls_str) in verified_authors.items():
                    logger.info(f"    [NOTABLE] {author} ({ev}){urls_str}")

                # Write final results to DB
                for author in chunk:
                    p = author_profiles[author]
                    is_notable = p["is_notable"]
                    ev = p["evidence"]
                    hp = p["homepage"]

                    if is_notable and author in verified_authors:
                        ev = verified_authors[author][0]
                        is_notable = True
                    elif is_notable and author in rejected_authors:
                        # Author was rejected by both web + LLM second opinion
                        is_notable = False
                        ev = rejected_authors[author][0]

                    upsert_author(
                        name=author, is_notable=is_notable, evidence=ev, homepage=hp
                    )

                # Phase 2.5 (Incremental): Attach notable authors to the citations in SQLite immediately
                # so the frontend can display them in real-time as each batch completes.
                import json
                for citation in collected_citations:
                    citation_id = citation["citation_id"]
                    notable_authors = []
                    for citation_author in citation["authors"]:
                        name = citation_author.get("name")
                        if not name:
                            continue
                        author_record = get_author(name)
                        if author_record and author_record.get("is_notable"):
                            notable_authors.append(
                                {
                                    "name": name,
                                    "evidence": author_record.get("evidence", ""),
                                    "homepage": author_record.get("homepage", ""),
                                }
                            )

                    if len(notable_authors) > 0:
                        update_citation_authors(citation_id, json.dumps(notable_authors), citation.get("target_id"))

                current_batch = i // chunk_size
                total_batches = (len(unknown_authors) - 1) // chunk_size + 1
                progress = 30 + int(((current_batch + 1) / total_batches) * 20)
                update_target_progress(target_id, "collecting", progress)

                break
            except Exception as e:
                action = handle_llm_error(e, attempt)
                if action == "abort":
                    return
                elif action == "skip":
                    break
