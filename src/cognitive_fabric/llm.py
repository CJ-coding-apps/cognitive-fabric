"""LLM client resolution for the Cognitive Fabric.

Returns provider-native clients (openai.OpenAI / anthropic.Anthropic) that
callers duck-type (`hasattr(client, "chat")` vs `"messages"`). Raises
LlmNotConfiguredError when no provider key/SDK is available so callers can
degrade gracefully instead of crashing.

The *model* is resolved the same way, and for the same reason. A model id
compiled into the package is a decision nobody made: it picks a vendor, a price
and a capability envelope at install time, and it goes stale only when the
provider retires the name -- which is to say, silently. There is no default
here. A provider is usable once a key *and* a model are configured, and
`get_model_name` names the setting that is missing when one is not.

A configured model is then checked against the provider's own models-list
endpoint, so a renamed or retired model fails as "not found; available: ..."
with the names that do exist, rather than as a 404 from inside a distillation
step hours later. The lookup is cached per process: it is the same answer for
every call, and not worth a network round trip each time.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from cognitive_fabric.config import Settings
from cognitive_fabric.config import settings as default_settings


class LlmNotConfiguredError(RuntimeError):
    """Raised when an LLM client is requested but no provider is configured."""


_OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
_ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"

# Anthropic rejects a request without a version header, the models list included.
_ANTHROPIC_VERSION = "2023-06-01"

_MODELS_TIMEOUT_SECONDS = 10.0

# Anthropic pages its model list; the others return it whole. Stopping after a
# bounded number of pages keeps a paginating or misbehaving endpoint from turning
# a preflight check into an unbounded walk.
_MAX_MODEL_PAGES = 10

# How many of the provider's names to put in the message: enough to recognise the
# right answer in, short enough to read in a terminal.
_MODELS_SHOWN = 10

_SETTING_FOR = {"openai": "openai_model", "anthropic": "anthropic_model"}
_ENV_FOR = {
    "openai": "COGNITIVE_FABRIC_OPENAI_MODEL",
    "anthropic": "COGNITIVE_FABRIC_ANTHROPIC_MODEL",
}
_DOCS_FOR = {
    "openai": "https://platform.openai.com/docs/models",
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models",
}

# (provider, model) -> the ids the provider reports. The lifetime of a process is
# the right lifetime for an answer that changes when a vendor ships.
_MODEL_LIST_CACHE: Dict[Tuple[str, str], List[str]] = {}


def get_model_name(
    settings: Optional[Settings] = None,
    provider: Optional[str] = None,
) -> str:
    """Return the configured model name for the active provider.

    Args:
        settings: Settings to read. Defaults to the process-wide settings.
        provider: Provider to resolve for, when the caller knows better than
            `settings.llm_provider`. The memory optimizer carries its own
            provider, and it must not silently fall back to the global one.

    Raises:
        LlmNotConfiguredError: if no model is configured for that provider.
    """
    settings = settings or default_settings
    provider = provider or settings.llm_provider

    model = getattr(settings, _SETTING_FOR[provider], None)
    if not model:
        raise LlmNotConfiguredError(
            f"no model is configured for {provider}: this project ships no "
            f"default, because a model id is a vendor, a price and a capability "
            f"envelope chosen at install time. Set {_ENV_FOR[provider]} to a "
            f"model id from {_DOCS_FOR[provider]}."
        )
    return str(model)


def _list_models(provider: str, api_key: str) -> List[str]:
    """Every model id the provider reports, in its own order.

    Uses the standard library rather than an HTTP client, so that a single GET
    does not add a dependency to this package.

    Raises whatever the transport raises: the caller distinguishes a rejected key
    from an unreachable catalog from a model that is simply not there.
    """
    models: List[str] = []
    after_id: Optional[str] = None

    for _ in range(_MAX_MODEL_PAGES):
        if provider == "anthropic":
            url = _ANTHROPIC_MODELS_URL
            if after_id:
                url = f"{url}?after_id={urllib.parse.quote(after_id, safe='')}"
            headers = {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_VERSION}
        else:
            url = _OPENAI_MODELS_URL
            headers = {"Authorization": f"Bearer {api_key}"}

        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(  # noqa: S310 - fixed https:// URLs above
            request, timeout=_MODELS_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read())

        models.extend(
            str(entry["id"]) for entry in payload.get("data", []) if "id" in entry
        )

        if not payload.get("has_more"):
            break
        after_id = payload.get("last_id")
        if not after_id:
            break

    return models


def _cloud_model_problem(provider: str, model: str, api_key: str) -> Optional[str]:
    """Why `model` cannot be used with `provider`, or None if it can.

    Unverifiable is reported as unverifiable rather than as verified. Letting a
    failed lookup through would be reasonable if the cost were a wrong answer
    nobody sees -- but the whole reason this exists is that a wrong model name
    surfaces as an opaque 404 later, and treating "could not check" as "fine"
    reproduces exactly that, one layer earlier.
    """
    cache_key = (provider, model)
    listed = _MODEL_LIST_CACHE.get(cache_key)

    if listed is None:
        try:
            listed = _list_models(provider, api_key)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return f"the {provider} API rejected the key (HTTP {e.code})"
            return (
                f"could not list {provider} models to check {model!r} "
                f"(HTTP {e.code}); the model is unverified, not confirmed"
            )
        except (urllib.error.URLError, OSError) as e:
            return (
                f"could not reach the {provider} model list to check {model!r} "
                f"({type(e).__name__}); the model is unverified, not confirmed"
            )
        except (ValueError, KeyError) as e:
            return (
                f"the {provider} model list did not parse ({type(e).__name__}); "
                f"{model!r} is unverified, not confirmed"
            )
        _MODEL_LIST_CACHE[cache_key] = listed

    if model in listed:
        return None

    shown = ", ".join(listed[:_MODELS_SHOWN]) or "none"
    more = ", ..." if len(listed) > _MODELS_SHOWN else ""
    return (
        f"{provider} does not list a model named {model!r} (available: {shown}{more})"
    )


def _reject_unusable_model(provider: str, model: str, api_key: str) -> None:
    """Raise if the provider does not list `model`.

    A raised LlmNotConfiguredError is how every caller here learns to degrade
    without an LLM, so a retired model name arrives as "skipped, and here is
    why" rather than as a 404 from inside a distillation step.
    """
    problem = _cloud_model_problem(provider, model, api_key)
    if problem:
        raise LlmNotConfiguredError(problem)


def get_llm_client(settings: Optional[Settings] = None) -> Any:
    """Resolve a provider-native LLM client.

    Raises:
        LlmNotConfiguredError: if the provider's model is unset, its API key is
            missing, its SDK cannot be imported, or the model it names is not one
            the provider currently lists.
    """
    settings = settings or default_settings
    provider = settings.llm_provider
    model = get_model_name(settings, provider)

    if provider == "anthropic":
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LlmNotConfiguredError("ANTHROPIC_API_KEY is not set")
        _reject_unusable_model(provider, model, api_key)
        try:
            from anthropic import Anthropic
        except Exception as e:  # pragma: no cover - SDK availability guard
            raise LlmNotConfiguredError(f"anthropic SDK unavailable: {e}") from e
        kwargs = (
            {"api_key": settings.anthropic_api_key}
            if settings.anthropic_api_key
            else {}
        )
        return Anthropic(**kwargs)

    # default: openai
    api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LlmNotConfiguredError("OPENAI_API_KEY is not set")
    _reject_unusable_model(provider, model, api_key)
    try:
        from openai import OpenAI
    except Exception as e:  # pragma: no cover - SDK availability guard
        raise LlmNotConfiguredError(f"openai SDK unavailable: {e}") from e
    kwargs = {"api_key": settings.openai_api_key} if settings.openai_api_key else {}
    return OpenAI(**kwargs)
