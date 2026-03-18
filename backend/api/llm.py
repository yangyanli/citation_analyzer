"""LLM client initialisation (Google Gemini via ``google-genai``)."""

import os
import time
import datetime
import tiktoken

from backend.core.config import logger
from backend.core.cost import increment_fallback_savings
from backend.database.sqlite_db import set_target_fallback_status

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_client_instance = None


class FallbackModelsBase:
    """Mock the models attribute of genai.Client or wrap a real one."""

    def __init__(self, run_dir: str, real_models=None):
        self.run_dir = run_dir
        self.call_indices = {}
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.real_models = real_models

    def generate_content(self, model: str, contents: str, config=None):
        mode_str = (
            "FALLBACK LLM MODE" if self.real_models is None else "LOGGING LLM MODE"
        )
        logger.info(f"\n[{mode_str}] Triggered for model: {model}")

        # Estimate input tokens using tiktoken (exact count)
        input_tokens = len(self.tokenizer.encode(contents))

        # Determine the stage from the caller-provided config (preferred) or fall back to "unknown"
        lower_contents = contents.lower()
        phase_stage = (
            config.get("phase") if isinstance(config, dict) else None
        ) or "unknown"

        # For the 2nd-opinion call, reuse the current phase_2_author index
        if phase_stage == "phase_2_author_round_2":
            index_str = f"{self.call_indices.get('phase_2_author', 1):06d}"
        else:
            self.call_indices[phase_stage] = self.call_indices.get(phase_stage, 0) + 1
            index_str = f"{self.call_indices[phase_stage]:06d}"

        # Determine strict output format
        is_json_expected = "json" in lower_contents
        output_ext = "json" if is_json_expected else "md"

        target_id = config.get("target_id") if isinstance(config, dict) else None
        system_user_id = (
            config.get("system_user_id") if isinstance(config, dict) else None
        )

        # File prefix: insert index after phase_X, e.g. phase_2_000001_author_round_1
        parts = phase_stage.split("_", 2)
        if len(parts) == 3 and parts[0] == "phase":
            file_prefix = f"phase_{parts[1]}_{index_str}_{parts[2]}"
        else:
            file_prefix = f"{phase_stage}_{index_str}"

        prompt_file = os.path.join(self.run_dir, f"{file_prefix}_prompt.txt")
        response_file = os.path.join(
            self.run_dir, f"{file_prefix}_response.{output_ext}"
        )

        from backend.database.sqlite_db import insert_llm_log

        run_id = os.path.basename(self.run_dir)

        try:
            # Normal path
            logger.info("⏳ Calling Gemini API...")
            real_response = self.real_models.generate_content(
                model=model, contents=contents, config=config
            )
            response_text = real_response.text

            output_tokens = len(self.tokenizer.encode(response_text))
            logger.info(f"⬅️  Received API response ({output_tokens} exact tokens).")

            # LOG TO DB
            insert_llm_log(
                {
                    "run_id": run_id,
                    "target_id": target_id,
                    "system_user_id": system_user_id,
                    "stage": phase_stage,
                    "model": model,
                    "prompt_text": contents,
                    "response_text": response_text,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "is_fallback": False,
                }
            )

            return real_response
            
        except Exception as e:
            # Fallback path
            if self.real_models is not None:
                logger.error(f"❌ Gemini API call failed: {e}")
                logger.warning(
                    "Falling back to manual intervention for this and subsequent requests."
                )
                self.real_models = None

            # Write native prompt to file in the specific run directory only if fallback mode
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(contents)

            logger.info(
                f"➡️  Wrote requested prompt to {prompt_file} ({input_tokens} exact tokens)."
            )

            # Explicit Terminal Alert (No specific agent instructions, just general human instructions)
            alert_msg = (
                f"\n--- MANUAL FALLBACK TRIGGERED ---\n"
                f"An LLM API call has failed or the API key is missing.\n"
                f"The system has paused and requires a human response to proceed.\n\n"
                f"INPUT PROMPT FILE:  {os.path.abspath(prompt_file)}\n"
                f"EXPECTED RESPONSE:  {os.path.abspath(response_file)}\n\n"
                f"Please read the input prompt file, write the appropriate response\n"
                f"exactly to the EXPECTED RESPONSE path, and ensure it meets any\n"
                f"format requirements (e.g. valid JSON if requested).\n"
                f"The system is actively monitoring that path and will resume automatically.\n"
                f"---------------------------------\n"
            )
            print(alert_msg)

            # Toggle DB UI State
            if target_id:
                try:
                    set_target_fallback_status(target_id, True)
                except Exception as e:
                    logger.warning(
                        f"Could not toggle fallback db state for {target_id}: {e}"
                    )

            logger.info("Polling for response file...")
            while not os.path.exists(response_file):
                time.sleep(0.5)

            # Untoggle DB UI State
            if target_id:
                try:
                    set_target_fallback_status(target_id, False)
                except Exception as e:
                    logger.warning(
                        f"Could not untoggle fallback db state for {target_id}: {e}"
                    )

            # Read native response
            try:
                with open(response_file, "r", encoding="utf-8") as f:
                    response_text = f.read()
            except FileNotFoundError:
                logger.error(
                    f"❌ Could not find {response_file}. Returning empty response."
                )
                response_text = "{}"

            # Estimate output tokens using tiktoken
            output_tokens = len(self.tokenizer.encode(response_text))
            logger.info(
                f"⬅️  Read response from {response_file} ({output_tokens} exact tokens)."
            )

            # Accumulate savings
            increment_fallback_savings(model, input_tokens, output_tokens)

            # LOG TO DB
            insert_llm_log(
                {
                    "run_id": run_id,
                    "target_id": target_id,
                    "system_user_id": system_user_id,
                    "stage": phase_stage,
                    "model": model,
                    "prompt_text": contents,
                    "response_text": response_text,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "is_fallback": True,
                }
            )

            # Return a mock response object with a .text attribute
            class MockResponse:
                def __init__(self, text):
                    self.text = text

            return MockResponse(response_text)

    def count_tokens(self, model: str, contents: str):
        if self.real_models:
            return self.real_models.count_tokens(model=model, contents=contents)

        # Provide an exact token count for cost estimation phase if it calls it
        class MockTokenCount:
            def __init__(self, total_tokens):
                self.total_tokens = total_tokens

        return MockTokenCount(len(self.tokenizer.encode(contents)))


class FallbackClient:
    """Fallback client that intercepts generate_content calls."""

    def __init__(self, real_client=None):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        llm_calls_base = os.environ.get(
            "LLM_CALLS_DIR", os.path.join(project_root, "llm_calls")
        )
        self.run_dir = os.path.join(llm_calls_base, f"run_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)
        self.models = FallbackModelsBase(
            self.run_dir, real_models=real_client.models if real_client else None
        )


def initialize_llm_client():
    """Initialise and return the Gemini API client or Fallback client. Save it to singleton."""
    global _client_instance

    # Optimistically try to initialize real client, even if key appears empty
    if GEMINI_API_KEY:
        try:
            from google import genai

            real_client = genai.Client()
            _client_instance = FallbackClient(real_client=real_client)
            logger.info(
                "Gemini LLM Client Initialized via API Key with file logging enabled."
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize Gemini client: {e}. Entering fallback mode."
            )
            _client_instance = FallbackClient()
    else:
        logger.warning(
            "No GEMINI_API_KEY found in environment variables. Entering fallback mode."
        )
        _client_instance = FallbackClient()

    return _client_instance


def get_llm_client():
    """Return the pre-initialised Gemini client (or ``None``)."""
    return _client_instance
