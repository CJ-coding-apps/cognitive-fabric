#!/usr/bin/env python
"""One tiny call per cloud provider, against the real APIs.

Everything else in this repository runs without a network. The unit tests that
cover request shape use fakes, which is what makes them fast and deterministic --
and also what makes them unable to answer the one question only a live call can:
does the model the operator configured still exist, and does the provider still
accept the request this package builds for it? A model id is retired by the
vendor on the vendor's schedule, and no amount of local testing notices.

So this is deliberately *not* part of CI's test jobs. It needs secrets, it costs
a fraction of a cent, and it fails for reasons that have nothing to do with the
commit under test. It runs weekly and on demand, on `main` only, via
`.github/workflows/live-provider-smoke.yml`.

The model comes from an environment variable the workflow reads out of the
repository's *variables* (not secrets -- a model id is not a credential, and
being able to see it makes a failure readable). The key comes from a secret.
A provider with no key configured is reported as skipped, never as passed:
silence is not success, and a workflow that goes green because it tested nothing
is worse than one that never ran.

Because the client is built through `get_llm_client`, this also exercises the
models-list preflight against the live endpoint -- the same check every real
call goes through, and the one that turns a retired model name into "not found;
available: ..." rather than a 404 from inside a service.

Run it locally with the same variables:

    OPENAI_API_KEY=sk-... OPENAI_MODEL=<a model id> \\
        .venv/bin/python scripts/live_provider_smoke.py
"""

import os
import sys

from cognitive_fabric.config import Settings
from cognitive_fabric.llm import LlmNotConfiguredError, get_llm_client

# Short enough that a provider billing by the token is not worth thinking about,
# and unambiguous enough that a wrong answer is visible at a glance.
PROMPT = "Reply with the single word: ok"
MAX_TOKENS = 16

OK = "ok"
SKIPPED = "skipped"
FAILED = "FAILED"

# (label, provider, key variable, model variable). Anthropic is not a Cohere
# substitute: this package speaks to exactly two LLM providers, and the smoke
# check covers the ones it ships.
PROVIDERS = [
    ("openai", "openai", "OPENAI_API_KEY", "OPENAI_MODEL"),
    ("anthropic", "anthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
]


def _check(label: str, provider: str, key_var: str, model_var: str):
    """Build one provider through the real resolution path and ask for one word."""
    key = os.environ.get(key_var)
    model = os.environ.get(model_var)

    if not key:
        return label, SKIPPED, f"{key_var} is not set"
    if not model:
        # A key with no model is the state this package now refuses to guess its
        # way out of, so the smoke check must not guess either.
        return (
            label,
            SKIPPED,
            f"{model_var} is not set (set it in the repository variables)",
        )

    # Settings takes the values directly, so the check does not depend on how the
    # repository happens to be configured at the time it runs.
    settings = Settings(
        llm_provider=provider,
        **{f"{provider}_api_key": key, f"{provider}_model": model},
    )

    try:
        client = get_llm_client(settings)
        if provider == "anthropic":
            resp = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": PROMPT}],
            )
            text = resp.content[0].text
        else:
            # `max_completion_tokens`, never `max_tokens`: the reasoning models
            # reject the older name, and the older models ignore the newer one.
            resp = client.chat.completions.create(
                model=model,
                max_completion_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": PROMPT}],
            )
            text = resp.choices[0].message.content
    except LlmNotConfiguredError as e:
        return label, FAILED, f"rejected at preflight: {e}"
    except Exception as e:  # noqa: BLE001 -- any failure here is the result
        return label, FAILED, f"{type(e).__name__}: {e}"

    if not (text or "").strip():
        return label, FAILED, "the provider returned no text"
    return label, OK, f"model={model!r} replied {text.strip()[:40]!r}"


def main() -> int:
    checks = [_check(*spec) for spec in PROVIDERS]

    width = max(len(label) for label, _, _ in checks)
    for label, verdict, detail in checks:
        print(f"{label:<{width}}  {verdict:<8}  {detail}")

    failed = [label for label, verdict, _ in checks if verdict == FAILED]
    skipped = [label for label, verdict, _ in checks if verdict == SKIPPED]
    passed = len(checks) - len(failed) - len(skipped)
    print(f"\n{passed} passed, {len(skipped)} skipped, {len(failed)} failed")

    if skipped:
        print(f"skipped (no key or no model configured): {', '.join(skipped)}")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    if passed == 0:
        print("Nothing was checked. Configure at least one provider.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
