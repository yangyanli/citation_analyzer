import sys
import argparse
from backend.core.config import logger

from backend.api.scholar import fetch_scholar_publications
from backend.api.semantic_scholar import search_semantic_scholar_paper, fetch_s2_author
from backend.pipeline.phase_0_criteria import generate_domain_criteria
from backend.pipeline.phase_1_citations import collect_citations
from backend.pipeline.phase_2_authors import evaluate_authors
from backend.pipeline.phase_3_seminal import evaluate_seminal_works
from backend.pipeline.phase_4_sentiment import score_citations
from backend.pipeline.phase_5_domains import classify_domains
from backend.core.cost import estimate_pipeline_cost, print_cost_table
from backend.core.cli import (
    prompt_model_selection,
    confirm_criteria,
    print_task_summary,
)
from backend.database.sqlite_db import (
    upsert_analysis_target,
    get_all_citations,
    get_unscored_citations,
    get_author,
    update_target_progress,
    update_target_s2_total,
    get_analysis_target,
    update_target_phase_estimates,
    update_target_total_citations,
    wipe_phase_data,
)
import os


def run_pipeline(args: argparse.Namespace, client, overrides: dict | None) -> None:
    """Executes the core semantic analysis pipeline."""
    target_id = None
    system_user_id = getattr(args, "system_user_id", None)
    
    # Check if a custom end-phase was supplied
    run_only_phase = getattr(args, "run_only_phase", None)

    # When re-running a single phase, ensure start_phase is at least that phase
    # so we skip all prior phases entirely.
    if run_only_phase is not None:
        if getattr(args, "start_phase", 0) < run_only_phase:
            args.start_phase = run_only_phase

    try:
        # --- Determine analysis mode ---
        if args.user_id:
            if args.user_id.isdigit():
                s2_author = fetch_s2_author(args.user_id)
                if not s2_author:
                    raise ValueError(
                        f"Could not find Semantic Scholar author with ID: {args.user_id}"
                    )
                scholar_name = s2_author.get("name", "")
                interests = []
                publications = [
                    {"bib": {"title": p["title"]}}
                    for p in s2_author.get("papers", [])
                    if p.get("title")
                ]
                analysis_target = {
                    "mode": "scholar",
                    "name": scholar_name,
                    "user_id": args.user_id,
                    "url": f"https://www.semanticscholar.org/author/{args.user_id}",
                    "interests": [],
                    "group_id": getattr(args, "group_id", None),
                }
            else:
                author_profile = fetch_scholar_publications(args.user_id)
                if not author_profile:
                    raise ValueError("No publications found.")

                scholar_name = author_profile.get("name", "")
                interests = author_profile.get("interests", [])
                publications = author_profile.get("publications", [])
                analysis_target = {
                    "mode": "scholar",
                    "name": scholar_name,
                    "user_id": args.user_id,
                    "url": f"https://scholar.google.com/citations?user={args.user_id}",
                    "interests": interests,
                    "group_id": getattr(args, "group_id", None),
                }
            target_id = args.user_id
            upsert_analysis_target(target_id, analysis_target)
            update_target_progress(target_id, "pending", 5)

            start_phase = getattr(args, "start_phase", 0)

            if start_phase == 0:
                print(
                    f"\nFound {len(publications)} publications for {scholar_name}. Starting phase 0: deducing domain criteria...\n"
                )
                eval_criteria = generate_domain_criteria(
                    client,
                    args.model,
                    target_id,
                    publications=publications,
                    scholar_name=scholar_name,
                    interests=interests,
                    overrides=overrides,
                    system_user_id=system_user_id,
                )
            else:
                print(
                    f"\nFound {len(publications)} publications for {scholar_name}. Skipping phase 0. Loading criteria from DB...\n"
                )
                target_data = get_analysis_target(target_id)
                if not target_data or not target_data.get("evaluation_criteria"):
                    raise ValueError(
                        f"Cannot skip phase 0: No criteria found in DB for {target_id}."
                    )
                eval_criteria = target_data["evaluation_criteria"]
        else:
            print(f"\nSearching Semantic Scholar for: '{args.paper}'...")
            s2_paper = search_semantic_scholar_paper(args.paper)

            if not s2_paper:
                raise ValueError(
                    f"Could not find paper '{args.paper}' on Semantic Scholar."
                )

            paper_title = s2_paper.get("title") or args.paper
            s2_url = f"https://www.semanticscholar.org/paper/{s2_paper['paperId']}"
            scholar_name = None
            publications = [{"bib": {"title": paper_title}}]
            analysis_target = {
                "mode": "paper",
                "title": paper_title,
                "s2_url": s2_url,
                "group_id": getattr(args, "group_id", None),
            }
            target_id = paper_title
            upsert_analysis_target(target_id, analysis_target)
            update_target_progress(target_id, "pending", 5)

            start_phase = getattr(args, "start_phase", 0)

            if start_phase == 0:
                print(
                    f"\nFound paper: '{paper_title}'. Starting phase 0: deducing domain criteria...\n"
                )
                eval_criteria = generate_domain_criteria(
                    client,
                    args.model,
                    target_id,
                    paper_title=paper_title,
                    overrides=overrides,
                    system_user_id=system_user_id,
                )
            else:
                print(
                    f"\nSkipping phase 0. Loading criteria for '{paper_title}' from database...\n"
                )
                target_data = get_analysis_target(target_id)
                if not target_data or not target_data.get("evaluation_criteria"):
                    raise ValueError(
                        f"Cannot skip phase 0: No criteria found in DB for {target_id}."
                    )
                eval_criteria = target_data["evaluation_criteria"]

        # --- Handle Overrides when skipping Phase 0 ---
        if start_phase > 0 and overrides:
            updated = False
            for k in ("domain", "notable_criteria", "seminal_criteria"):
                if overrides.get(k) and overrides[k] != eval_criteria.get(k):
                    eval_criteria[k] = overrides.get(k)
                    updated = True
            if updated:
                print(f"\nUpdating criteria in DB from user overrides...")
                target_data = get_analysis_target(target_id)
                if target_data:
                    target_data["evaluation_criteria"] = eval_criteria
                    upsert_analysis_target(target_id, target_data)

        # --- Handle Wiping ---
        wipe_phase = getattr(args, "wipe_phase", None)
        if wipe_phase is not None:
            print(f"\n--- Wiping Phase {wipe_phase} ---")
            wipe_phase_data(target_id, wipe_phase)
            
            # Wipe LLM cache for this target/phase
            try:
                # Find the most recently run llm_calls folder or just wipe broadly across llm_calls
                llm_calls_dir = "llm_calls"
                if os.path.exists(llm_calls_dir):
                    wiped_count = 0
                    for root, _, files in os.walk(llm_calls_dir):
                        for file in files:
                            if file.startswith(f"phase_{wipe_phase}_"):
                                os.remove(os.path.join(root, file))
                                wiped_count += 1
                    print(f"✅ Cleared {wiped_count} LLM cache files for phase {wipe_phase}.")
            except Exception as e:
                logger.warning(f"Error clearing cache files: {e}")
            
            print(f"✅ Phase {wipe_phase} data completely wiped.")
            
            # If start_phase wasn't explicitly provided, or if user ONLY wanted to wipe, exit.
            # But the user mentioned `--wipe_phase 3` as a command, so if they didn't specify start_phase or run_only, 
            # we should probably just continue if they used --start_phase, but let's just let it naturally flow since start_phase defaults to 0.
            # Actually, if we're wiping, we might want to just exit unless they explicitly want to run.
            # Let's see if run_only_phase or start_phase is set to determine if we should stop.
            if run_only_phase is None and getattr(args, "start_phase", 0) == 0 and not getattr(args, "user_id", None) and not getattr(args, "paper", None):
                 # This is tricky because start_phase defaults to 0. Let's just rely on the user to use run_only_phase if they want a specific action.
                 pass

        # True if user supplied all three criteria (no LLM inference needed)
        all_criteria_supplied = overrides is not None and all(
            overrides.get(k) for k in ("domain", "notable_criteria", "seminal_criteria")
        )

        if getattr(args, "generate_criteria_only", False):
            import json

            print(
                f"---CRITERIA_JSON_START---{json.dumps(eval_criteria)}---CRITERIA_JSON_END---"
            )
            sys.exit(0)

        # --- Interactive criteria confirmation ---
        if (
            start_phase == 0
            and not all_criteria_supplied
        ):
            eval_criteria = confirm_criteria(target_id, eval_criteria, non_interactive=getattr(args, "non_interactive", False))

        # Set total_citations for frontend progress tracking
        if args.total_citations_to_add != "all":
            update_target_total_citations(target_id, int(args.total_citations_to_add))

        # --- Phase 1: Citation collection ---
        # NOTE: print_task_summary is deferred to AFTER this phase.
        # Citation collection populates the S2 cache, so the summary
        # can then use cached data instead of making 100+ individual API calls.
        if start_phase <= 1 and (run_only_phase is None or run_only_phase == 1):
            print("\nStarting phase 1: collecting citations...\n")
            update_target_progress(target_id, "collecting", 12)
            collected_citations = collect_citations(
                publications, scholar_name, args.total_citations_to_add, target_id
            )
            update_target_progress(target_id, "collecting", 25)
        else:
            print("\nSkipping phase 1. Loading collected citations from database...\n")
            # We strictly need to collect the uncached missing citations to avoid
            # over-evaluating everything for pricing and passing the right list to evaluate_authors
            # But the phase2 function expects the citations dictionaries for retrieving their nested authors list
            collected_citations = get_all_citations(target_id)

        all_citations = get_all_citations(target_id)
        todo_count = len(get_unscored_citations(target_id))
        finished_count = len(all_citations) - todo_count

        # Always update total_citations with actual DB count for frontend accuracy
        update_target_total_citations(target_id, len(all_citations))

        # --- Deferred S2 total and cost estimation (skip if re-running single phase) ---
        phase_costs = {2: {"batches": 0, "cost": 0.0}, 3: {"batches": 0, "cost": 0.0}, 4: {"batches": 0, "cost": 0.0}, 5: {"batches": 0, "cost": 0.0}}

        if run_only_phase is not None:
            # Fast path: skip S2 fetch, cost estimation, and model prompt
            print(f"\n--- Re-running Phase {run_only_phase} only ---")
            print(f"Loaded {len(collected_citations):,} citations ({todo_count:,} unscored).")
            print(f"Proceeding with {args.model}...\n")
        else:
            if start_phase <= 1:
                total_citations_s2 = print_task_summary(target_id, publications)
                update_target_s2_total(target_id, total_citations_s2)
            else:
                # If we skipped Phase 1, just use the saved DB value (or standard cache)
                target_data_s2 = get_analysis_target(target_id)
                total_citations_s2 = target_data_s2.get("s2_total_citations", len(all_citations)) if target_data_s2 else len(all_citations)

            # --- Cost & Time estimation ---
            unknown_authors = list(
                {
                    (author.get("name") if isinstance(author, dict) else author)
                    for citation in collected_citations
                    for author in citation["authors"]
                    if (author.get("name") if isinstance(author, dict) else author) and 
                       get_author((author.get("name") if isinstance(author, dict) else author)) is None
                }
            )

            num_unknown = len(unknown_authors)
            num_unscored = todo_count

            est_seconds = 0
            if num_unknown > 0:
                est_seconds += (num_unknown * 1.5) + ((num_unknown // 80 + 1) * 10)
            if num_unscored > 0:
                est_seconds += (num_unscored * 0.8) + ((num_unscored // 20 + 1) * 10)

            est_str = "Calculating..."
            if est_seconds > 0:
                mins = int(est_seconds // 60)
                secs = int(est_seconds % 60)
                est_str = f"~{mins}m {secs}s" if mins > 0 else f"~{secs}s"
            else:
                est_str = "Near instantaneous (cached)"

            print("\n--- Task Summary ---")
            print(
                f"Target: {analysis_target.get('name') or analysis_target.get('title')}"
            )
            print(f"Total Citations on S2: {total_citations_s2:,}")
            print(f"Fully Cached / Finished: {finished_count:,}")
            print(f"Pending in this run: {todo_count:,}")
            print(f"Est. Time Remaining: {est_str}")
            print("--------------------")

            if not collected_citations:
                print("No new citations to process.")
                update_target_progress(target_id, "completed", 100)
                return

            # --- Cost table ---
            if start_phase <= 1:
                uncached_citations = collected_citations
            else:
                uncached_citations = get_unscored_citations(target_id)

            if (unknown_authors or uncached_citations):
                estimates = estimate_pipeline_cost(
                    unknown_authors, uncached_citations, eval_criteria
                )
                print_cost_table(
                    unknown_authors, uncached_citations, estimates
                )

                from backend.core.cost import compute_phase_costs
                phase_costs = compute_phase_costs(estimates, args.model)
                for phase_num, pc in phase_costs.items():
                    if phase_num >= start_phase or start_phase <= 1:
                        update_target_phase_estimates(target_id, phase_num, pc["batches"], pc["cost"])

                if args.estimate_only:
                    print("\nEstimation run complete. Exiting.")
                    return

                old_model = args.model
                selected = prompt_model_selection(args.model, non_interactive=getattr(args, "non_interactive", False))
                if selected is None:
                    print("Aborted by user.")
                    return
                args.model = selected
                
                if selected != old_model:
                    phase_costs = compute_phase_costs(estimates, args.model)
                    for phase_num, pc in phase_costs.items():
                        if phase_num >= start_phase or start_phase <= 1:
                            update_target_phase_estimates(target_id, phase_num, pc["batches"], pc["cost"])

                print(f"\nProceeding with {args.model}...\n")

        # --- Phase 2: Notable Authors ---
        if start_phase <= 2 and (run_only_phase is None or run_only_phase == 2):
            print(f"\n[Phase 2 - Authors] Expected Batches: {phase_costs[2].get('batches', 0)} | Estimated Cost: ${phase_costs[2].get('cost', 0.0):.4f}")
            evaluate_authors(
                client, args.model, eval_criteria, collected_citations, target_id, system_user_id=system_user_id
            )
        else:
            print("\nSkipping phase 2. Authors are already evaluated.\n")

        # --- Phase 3: Sentiment & Seminal Discovery ---
        # NOTE: You can pass a custom 'scorer' (implementing CitationScorer) here
        # for future items like Multi-Model Consensus or Section-Aware Analysis.
        if start_phase <= 3 and (run_only_phase is None or run_only_phase == 3):
            print(f"\n[Phase 3 - Seminal] Expected Batches: {phase_costs[3].get('batches', 0)} | Estimated Cost: ${phase_costs[3].get('cost', 0.0):.4f}")
            evaluate_seminal_works(
                client, args.model, eval_criteria, target_id, system_user_id=system_user_id
            )
        else:
            print("\nSkipping phase 3. Seminal papers are already evaluated.\n")

        if start_phase <= 4 and (run_only_phase is None or run_only_phase == 4):
            print(f"\n[Phase 4 - Sentiment] Expected Batches: {phase_costs[4].get('batches', 0)} | Estimated Cost: ${phase_costs[4].get('cost', 0.0):.4f}")
            score_citations(client, args.model, eval_criteria, target_id, system_user_id=system_user_id)
        else:
            print("\nSkipping phase 4. Sentiment is already evaluated.\n")

        # --- Phase 5: Research Domain Classification ---
        if start_phase <= 5 and (run_only_phase is None or run_only_phase == 5):
            print(f"\n[Phase 5 - Domains] Expected Batches: {phase_costs[5].get('batches', 0)} | Estimated Cost: ${phase_costs[5].get('cost', 0.0):.4f}")
            print("Classifying research domains...")
            classify_domains(client, args.model, eval_criteria, target_id, system_user_id=system_user_id)
        else:
            print("\nSkipping phase 5. Domains are already classified.\n")

        # Final update
        update_target_progress(target_id, "completed", 100)
        print("\n✅ Analysis complete. View results in the dashboard.")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if target_id:
            update_target_progress(target_id, "failed", 0, str(e))
        raise e
