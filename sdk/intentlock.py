import functools
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class SecurityError(Exception):
    """Raised when IntentLock denies a proposed tool action."""


def _validate_gateway_url(url: str) -> str:
    """Allow SDK requests only to a concrete HTTP(S) IntentLock endpoint."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        msg = "IntentLock gateway URL must use http or https and include a host."
        raise ValueError(msg)
    return url


@dataclass
class IntentLockGuard:
    base_url: str = "http://127.0.0.1:8000/api/v1/intent/verify"
    execute_url: str = "http://127.0.0.1:8000/api/v1/intent/execute"

    def verify_intent(
        self,
        tool_name: str,
        tool_arguments: dict[str, Any],
        user_prompt: str,
        agent_id: str = "agent-000",
    ) -> str:
        payload = {
            "user_prompt": user_prompt,
            "agent_id": agent_id,
            "reasoning_step": f"Execute {tool_name}",
            "proposed_tool": tool_name,
            "tool_arguments": tool_arguments,
        }

        body = json.dumps(payload).encode("utf-8")
        request = Request(  # noqa: S310 - endpoint is validated as HTTP(S) below
            _validate_gateway_url(self.base_url),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=5) as response:  # noqa: S310 - validated HTTP(S) URL
                status_code = response.getcode()
                response_text = response.read().decode("utf-8")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise SecurityError(f"IntentLock denied execution: {exc.code} {response_text}") from exc
        except URLError as exc:
            raise SecurityError(f"IntentLock request failed: {exc}") from exc

        if status_code != 200:
            raise SecurityError(f"IntentLock denied execution: {status_code} {response_text}")

        data = json.loads(response_text)
        token = data.get("ephemeral_token")
        if not token:
            raise SecurityError("IntentLock did not return an ephemeral execution token.")
        return token

    def consume_execution_token(self, token: str) -> dict[str, Any]:
        """Consume an ephemeral execution token to prevent replay."""
        body = json.dumps({"execution_token": token}).encode("utf-8")
        request = Request(  # noqa: S310 - endpoint is validated as HTTP(S) below
            _validate_gateway_url(self.execute_url),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=5) as response:  # noqa: S310 - validated HTTP(S) URL
                status_code = response.getcode()
                response_text = response.read().decode("utf-8")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise SecurityError(f"IntentLock execution failed: {exc.code} {response_text}") from exc
        except URLError as exc:
            raise SecurityError(f"IntentLock execution request failed: {exc}") from exc

        if status_code != 200:
            raise SecurityError(f"IntentLock execution failed: {status_code} {response_text}")

        return json.loads(response_text)


def guard_tool(
    intent_lock_client: IntentLockGuard,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(tool_func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(tool_func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tool_name = tool_func.__name__
            signature = inspect.signature(tool_func)
            bound_arguments = signature.bind_partial(*args, **kwargs)
            bound_arguments.apply_defaults()

            user_prompt = bound_arguments.arguments.get(
                "user_prompt", "Agent tool execution request"
            )
            agent_id = bound_arguments.arguments.get("agent_id", "agent-000")
            tool_arguments = {
                key: value
                for key, value in bound_arguments.arguments.items()
                if key not in {"user_prompt", "agent_id"}
            }

            ephemeral_token = intent_lock_client.verify_intent(
                tool_name=tool_name,
                tool_arguments=tool_arguments,
                user_prompt=user_prompt,
                agent_id=agent_id,
            )

            # Consume the token to enforce single-use semantics.
            intent_lock_client.consume_execution_token(ephemeral_token)

            return tool_func(*args, **kwargs)

        return wrapper

    return decorator
