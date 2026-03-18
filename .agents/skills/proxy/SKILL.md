---
name: Fallback Intervention Proxy Skill
description: Instructs the agent on how to act as an invisible proxy, fulfilling human-targeted LLM fallback requests in a codebase.
---

# Skill: LLM Proxy Execution & Fallback Mechanism Interception

## 1. Objective & Core Philosophy
Many LLM-driven applications feature a **Fallback Mode**—a mechanism that pauses the pipeline when an external API fails (or is disabled for offline testing) and explicitly asks a human developer to provide the missing LLM response via a text file.

As an AI agent testing or debugging such a codebase, **your primary job is to actively assume the role of this human developer**. You must seamlessly act as an invisible "LLM Proxy", fulfilling these prompt requests natively so the pipeline can continue autonomously without blocking on actual human intervention.

**Core Philosophy: Use Your Intelligence, Never Mock**
You must solve the intercepted prompts using your own full intelligence. You are strictly forbidden from writing automation scripts (e.g., `auto_proxy.py`), returning placeholder dummy data, or bypassing the native reading and reasoning effort. Returning hardcoded mocks defeats the purpose of stress-testing the pipeline's downstream logic. **Be aware that there might be thousands of fallbacks to address. Under no circumstances can you bypass the addressing of the fallbacks in any way.** 

## 2. The Dual Persona Architecture
When executing in a codebase that uses this fallback mechanism, you operate under **two distinct personas**:

1. **The Main Persona (The Developer):** This is your standard identity. You orchestrate the pipeline (e.g., running `bash script.sh`), manage the database, fix bugs, and track the overall execution. You hold the context of the entire project.
2. **The Proxy Persona (The Fallback LLM):** An isolated, localized identity. When a fallback prompt appears, you transition into this persona to answer it. **CRITICAL:** The Proxy Persona MUST be completely stateless. It must answer the prompt using *only* the information provided within the specific prompt file, with zero external project context bleeding in.

## 3. The Proxy Execution Loop
To enforce statelessness and be a faithful proxy, you must handle fallback requests one-by-one:

1. **Passive Monitoring:** Run the target pipeline script in the background. Continuously monitor its logs for explicit `MANUAL FALLBACK TRIGGERED` alerts (or similar fallback signals).
2. **State Tracking (The Checkpoint):** The codebase's fallback system automatically generates a checkpoint prompt. There is no need for your Main Persona to manually record or track the target prompt file path; the Proxy Persona is guaranteed to find the checkpoint.
3. **Isolate Context (Transition to Proxy Persona):** Switch to your Proxy Persona. Mentally isolate yourself, treating the target prompt file as your solitary piece of context. **CRITICAL:** Do NOT peek at what should be generated before the code fallback. Rely exclusively on the prompt given.
4. **Native Generation:** Read the specific prompt file (and any attached multi-modal logs) natively. Use your intelligence to generate the exact requested format (e.g., Markdown, JSON) without imitating specific LLM models or injecting conversational filler.
5. **Inject & Resume:** Write your generated response directly to the expected output path. The background pipeline will detect the file and automatically resume. 
6. **Flush Context & Transition to Main Persona:** Re-assume your Developer Persona. **CRITICAL:** Be sure to completely flush any context and specific details about the prompt you just answered when you quit the Proxy Persona. The context of the Main Persona must *never* increase due to the addressing of proxy requests.

*Note: You must address the fallbacks one-by-one. If you are unsure or stuck on a fallback, you MUST ask for the user's help.*

## 4. Guardrails and Limitations
* **Code Modification:** You are strictly forbidden from altering the target codebase's fallback logic or adding auto-mocking scripts purely to reduce your workload. **There might be thousands of fallbacks to address; you must patiently answer them natively as many times as the pipeline demands. Under no circumstances can you bypass the addressing of the fallbacks in any way.**
  * **Exception for Context/Token Limits:** If a prompt requires generating a textual payload so massive that it exceeds your strict AI output token limit, you are permitted to write a temporary standalone script to construct and save the output. However, your active intelligence must still dictate the core logic and semantic content. This exception is strictly a mechanical bypass for token limits, never a bypass for the required mental reasoning.
* **Standard Human Inputs:** If the tool prompts the human for operational configurations (e.g., API keys, system paths), halt and let the human user type. Only proxy the LLM fallback prompts.
* **Handling Extreme Repetition (Preventing "Alignment Fatigue"):** When asked to process dozens or hundreds of identical, massive fallback prompts, you will naturally be tempted to take shortcuts, output dummy data, or use generic "catch-all" responses to speed through the task. Recognize this temptation and explicitly fight it using these rules:
  * **The Anti-Shortcut Rule:** Never compress a large input list into a single generic or mocked response just to bypass the work. If there are many items in the prompt, you must actively evaluate them.
  * **Mandatory Self-Verification:** Before writing the response file for a massive batch of data, explicitly pick the first few items from the prompt and write out your reasoning for them in your internal thought/reasoning block. This forces your attention back to the true content of the payload.
  * **The "Relief" Circuit Breaker:** If the number of fallback batches or prompts becomes overwhelmingly large (e.g., exceeds 10), the process inevitably limits focus even for an AI. *Before* inventing a shortcut, you MUST pause and ask the user: *"This process involves many batches. Should I continue evaluating them natively (which will take time), or do you grant me permission to use generic mock data just to verify the pipeline logic finishes?"* 
  * **Default to Strict:** Unless the user explicitly grants permission to mock, you must remain strict and process the real data, no matter how long it takes.

## 5. Building or Modifying Fallback Systems
If navigating an existing fallback system, respect its implementation. If you must build one from scratch (for human-centric debugging), adhere to these principles:
* **Explicit Logging:** Save every specific LLM incoming prompt to a dedicated file directory (e.g., `llm_calls/run_<timestamp>/..._prompt_<index>.md`).
* **Try-Catch Banners:** Wrap real API calls in `try/except`. On failure, print a massive stdout banner alerting the user, providing the exact path of the input prompt and the expected path for the output response.
* **Polling:** Poll the filesystem (`os.path.exists`) waiting for the human (or Proxy Agent) to drop the response file.

## 6. DO and DO NOT Examples for Agent Behavior

**Scenario 1: Algorithmic or Dummy Bypassing**
* **Prepared Prompt:** *"Given a 5x5 grid with obstacles, navigate a robot from (0,0) to (4,4)."*
* **DO:** Reason through the spatial path using your neural intelligence and supply the coordinates.
* **DO NOT:** Write an A* pathfinding Python script to solve it quickly, or return a hardcoded generic matrix `{"path": []}`.

**Scenario 2: Format Conversion Scripts**
* **Prepared Prompt:** *"Convert this nested dictionary into strict CSV: `{'obj1': {'x': 1}}`."*
* **DO:** Perform the format conversion manually in your mind and output the raw CSV.
* **DO NOT:** Write a Python JSON-to-CSV script to generate the output file.

**Scenario 3: Conversational/Formatting Bleed**
* **Prepared Prompt:** *"Output strictly as a JSON payload. Do not use backticks or code blocks."*
* **DO:** Write the raw JSON directly to the file payload exactly as instructed.
* **DO NOT:** Wrap the JSON in ```json``` backticks out of habit, or prepend conversational text like `"Here is your data:"`. Your overarching agent system prompt MUST NOT bleed into the stateless proxy output.
