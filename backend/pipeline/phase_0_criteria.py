"""Phase 0 — Dynamic domain-adaptive evaluation criteria generation.

Queries the LLM to infer the researcher's domain and produce tailored
criteria for notable-author and seminal-discovery classification.
Supports scholar mode, paper mode, and full CLI overrides.
"""

import datetime


from backend.core.config import logger, extract_json


def generate_domain_criteria(
    client,
    model_name: str,
    target_id: str,
    publications=None,
    paper_title: str | None = None,
    scholar_name: str | None = None,
    interests: list | None = None,
    overrides: dict | None = None,
    system_user_id: int | None = None,
) -> dict:
    """Generate domain-adaptive evaluation criteria strictly separated into two LLM calls.

    1. Infer Domain: Passes the scholar/paper abstracts to the LLM to deduce the domain.
    2. Generate Criteria: Uses ONLY the inferred domain to formulate the criteria.
    """

    from backend.database.sqlite_db import get_analysis_target, upsert_analysis_target
    from backend.api.semantic_scholar import search_semantic_scholar_paper

    # 0. Check overrides
    if overrides and all(
        overrides.get(k) for k in ("domain", "notable_criteria", "seminal_criteria")
    ):
        criteria = {
            "inferred_domain": overrides["domain"],
            "notable_criteria": overrides["notable_criteria"],
            "seminal_criteria": overrides["seminal_criteria"],
        }
        target_data = get_analysis_target(target_id) or {}
        target_data["evaluation_criteria"] = criteria
        upsert_analysis_target(target_id, target_data)
        logger.info(
            f"  [OVERRIDE] Using user-specified domain: {criteria['inferred_domain']}"
        )
        return criteria

    target_data = get_analysis_target(target_id) or {}
    existing_criteria = target_data.get("evaluation_criteria", {})
    if existing_criteria:
        logger.info(f"  [CACHE] Using existing criteria for: {target_id}")
        return existing_criteria

    logger.info(
        "  Generating domain-adaptive evaluation criteria via Gemini (Two-Phase)..."
    )

    # --- PHASE 0.1: Gather Context (Titles + Abstracts) ---
    paper_context_str = ""
    domain_hint = ""
    if overrides and overrides.get("domain"):
        domain_hint = f"\nThe research domain is: {overrides['domain']}. Use this as the inferred_domain."

    if scholar_name and publications:
        interest_list = interests or []
        current_year = datetime.datetime.now().year

        # We need to fetch abstracts for the top 5 and recent 5
        top_pub_titles = [
            pub["bib"].get("title")
            for pub in publications[:5]
            if pub.get("bib", {}).get("title")
        ]
        recent_pubs = [
            pub["bib"].get("title")
            for pub in publications
            if pub.get("bib", {}).get("title")
            and int(pub.get("bib", {}).get("pub_year", 0) or 0) >= current_year - 5
        ][:5]

        all_titles_to_fetch = list(set(top_pub_titles + recent_pubs))
        paper_context_str = f"Scholar: {scholar_name}\nResearch Interests: {', '.join(interest_list)}\n\nPublications:\n"
        for p in all_titles_to_fetch:
            paper_context_str += f"- Title: {p}\n"

    elif paper_title:
        s2_res = search_semantic_scholar_paper(paper_title)
        paper_context_str = f"Paper: {paper_title}\nAbstract: N/A"
    else:
        paper_context_str = "General Science"

    # --- PHASE 0.2: LLM Call 1 - Infer Domain ---
    domain_prompt = (
        f"You are an expert academic analyst. Based on the following context, infer the researcher's "
        f"core research domains (use multiple if applicable — e.g. 'Physics, Sociology, Biology').{domain_hint}\n\n"
        f"Context:\n{paper_context_str}\n\n"
        f"Respond ONLY with a JSON object containing a single key 'inferred_domain' with a string value of the domains.\n"
        f'{{"inferred_domain": "..."}}\n'
    )

    try:
        logger.info("  [Phase 0 - Call 1] Inferring Domain from publications...")
        response1 = client.models.generate_content(
            model=model_name,
            contents=domain_prompt,
            config={
                "phase": "phase_0_domain",
                "temperature": 0.2,
                "top_p": 0.8,
                "target_id": target_id,
                "system_user_id": system_user_id,
            },
        )
        domain_json = extract_json(response1.text)
        inferred_domain = domain_json.get("inferred_domain", "General Science")

        if overrides and overrides.get("domain"):
            inferred_domain = overrides["domain"]

        logger.info(f"  [SUCCESS] Deduced Domain: {inferred_domain}")
    except Exception as e:
        logger.error(f"  Failed to infer domain: {e}")
        inferred_domain = "General Science"

    # --- PHASE 0.3: LLM Call 2 - Generate Criteria from Domain ---
    criteria_prompt = (
        f"You are an expert academic analyst. The target research domain is: {inferred_domain}\n\n"
        f"Formulate evaluation criteria based STRICTLY and ONLY on this inferred domain. "
        f"Do NOT reference or tailor these criteria to any specific papers or authors.\n\n"
        f"1. NOTABLE AUTHORS: Build a tiered list:\n"
        f"   - Tier 1: Nobel Prize winners and each domain's equivalent highest honor "
        f"(e.g., Turing Award for CS, Fields Medal for Math, Lasker Award for Medicine, Pulitzer Prize for Journalism — identify the right one).\n"
        f"   - Tier 2: Best Paper / Test-of-Time Award winners at the domain's top-tier venues "
        f"(identify the prominent conferences, journals, or book awards for that specific field).\n"
        f"   - Tier 3: Fellows of major societies (e.g., IEEE Fellow, APS Fellow, MLA Fellow) and recipients "
        f"of significant career/lifetime achievement awards in the domain.\n"
        f"   Be inclusive across the domain so as not to exclude notable authors from adjacent fields.\n\n"
        f"2. SEMINAL DISCOVERIES: Build a tiered list for what defines a 'Seminal Discovery' in {inferred_domain}:\n"
        f"   - Tier 1: Groundbreaking theoretical or methodological papers that initiated entirely new subfields or paradigms.\n"
        f"   - Tier 2: Highly cited, transformative papers that solved long-standing open problems or became the standard baseline in {inferred_domain}. Often recognized with Best Paper or Test-of-Time awards at top venues.\n"
        f"   - Tier 3: Important papers that introduced widely adopted tools, datasets, or libraries essential to modern workflows in the domain.\n\n"
        f"Respond strictly in JSON:\n"
        f'{{"notable_criteria": "...", "seminal_criteria": "..."}}\n'
    )

    try:
        logger.info("  [Phase 0 - Call 2] Formulating Criteria based on Domain...")
        response2 = client.models.generate_content(
            model=model_name,
            contents=criteria_prompt,
            config={
                "phase": "phase_0_criteria",
                "temperature": 0.2,
                "top_p": 0.8,
                "target_id": target_id,
                "system_user_id": system_user_id,
            },
        )
        criteria_json = extract_json(response2.text)

        # Re-attach the domain for the return object
        criteria_json["inferred_domain"] = inferred_domain

        # Ensure strings
        for k in ["inferred_domain", "notable_criteria", "seminal_criteria"]:
            if k in criteria_json and not isinstance(criteria_json[k], str):
                if isinstance(criteria_json[k], dict):
                    criteria_json[k] = " ".join(
                        str(v) for v in criteria_json[k].values()
                    )
                elif isinstance(criteria_json[k], list):
                    criteria_json[k] = ", ".join(str(v) for v in criteria_json[k])
                else:
                    criteria_json[k] = str(criteria_json[k])

        # Apply overrides
        if overrides:
            if overrides.get("notable_criteria"):
                criteria_json["notable_criteria"] = overrides["notable_criteria"]
            if overrides.get("seminal_criteria"):
                criteria_json["seminal_criteria"] = overrides["seminal_criteria"]

        # Save
        target_data = get_analysis_target(target_id) or {}
        target_data["evaluation_criteria"] = criteria_json
        upsert_analysis_target(target_id, target_data)

        logger.info(f"  [NOTABLE] {criteria_json.get('notable_criteria')}")
        logger.info(f"  [SEMINAL] {criteria_json.get('seminal_criteria')}")

    except Exception as e:
        logger.error(f"  Failed to generate adaptive criteria: {e}")
        raise SystemExit(
            "\n❌ Could not auto-generate evaluation criteria.\n"
            "   Please provide them manually via CLI flags or a config file:\n\n"
            "   python3 main.py ... --config criteria.json\n\n"
            "   Example criteria.json:\n"
            '   {"domain": "General Science", "notable_criteria": "...", "seminal_criteria": "..."}\n'
        )

    return criteria_json
