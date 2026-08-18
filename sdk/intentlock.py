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
    """Raised when IntentLock denies a proposed tool action.

    This exception is raised when the gateway returns a non-200 status,
    when network errors occur, or when the response does not contain
    a valid execution token.
    """


def _validate_gateway_url(url: str) -> str:
    """Validate that the gateway URL uses HTTP or HTTPS and includes a host.

    Args:
        url: The gateway URL to validate.

    Returns:
        The validated URL.

    Raises:
        ValueError: If the URL does not use HTTP(S) or lacks a host.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        msg = "IntentLock gateway URL must use http or https and include a host."
        raise ValueError(msg)
    return url


@dataclass
class IntentLockGuard:
    """Client for the IntentLock proof-of-intent gateway.

    This class provides methods to verify intents and consume execution
    tokens via the IntentLock API. It enforces single-use semantics by
    consuming tokens immediately after verification.

    Attributes:
        base_url: The URL of the intent verification endpoint.
        execute_url: The URL of the token execution endpoint.
        auth_token: Optional bearer token for authenticated endpoints.
    """

    base_url: str = "http://127.0.0.1:8000/api/v1/intent/verify"
    execute_url: str = "http://127.0.0.1:8000/api/v1/intent/execute"
    auth_token: str | None = None

    def _auth_headers(self) -> dict[str, str]:
        """Build HTTP headers for API requests.

        Returns:
            A dictionary containing Authorization header if auth_token is set,
            otherwise only Content-Type.
        """
        if self.auth_token:
            return {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }
        return {"Content-Type": "application/json"}

    def verify_intent(
        self,
        tool_name: str,
        tool_arguments: dict[str, Any],
        user_prompt: str,
        agent_id: str = "agent-000",
    ) -> str:
        """Verify an intent with the gateway and return an execution token.

        Sends the proposed action to the gateway for evaluation. If the
        action is permitted, the gateway returns an ephemeral Ed25519
        execution token that can be consumed exactly once.

        Args:
            tool_name: The name of the tool being invoked.
            tool_arguments: The arguments being passed to the tool.
            user_prompt: The user's original prompt or request.
            agent_id: The identifier of the calling agent.

        Returns:
            A string containing the ephemeral execution token.

        Raises:
            SecurityError: If the gateway denies the action or a network
                error occurs.
        """
        payload = {
            "user_prompt": user_prompt,
            "agent_id": agent_id,
            "reasoning_step": f"Execute {tool_name}",
            "proposed_tool": tool_name,
            "tool_arguments": tool_arguments,
        }

        body = json.dumps(payload).encode("utf-8")
        request = Request(  # noqa: S310
            _validate_gateway_url(self.base_url),
            data=body,
            headers=self._auth_headers(),
            method="POST",
        )

        try:
            with urlopen(request, timeout=5) as response:  # nosec B310 - validated HTTP(S) URL above  # nosem  # noqa: S310
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
        token: str = data.get("ephemeral_token")
        if not token:
            raise SecurityError("IntentLock did not return an ephemeral execution token.")
        return token

    def consume_execution_token(self, token: str) -> dict[str, Any]:
        """Consume an ephemeral execution token to prevent replay.

        Sends the token to the gateway's execute endpoint. The gateway
        atomically consumes the token's nonce, rejecting any subsequent
        replay attempts.

        Args:
            token: The ephemeral execution token to consume.

        Returns:
            A dictionary containing the execution result from the gateway.

        Raises:
            SecurityError: If the token is invalid, expired, replayed,
                or a network error occurs.
        """
        body = json.dumps({"execution_token": token}).encode("utf-8")
        request = Request(  # noqa: S310
            _validate_gateway_url(self.execute_url),
            data=body,
            headers=self._auth_headers(),
            method="POST",
        )

        try:
            with urlopen(request, timeout=5) as response:  # nosec B310 - validated HTTP(S) URL above  # nosem  # noqa: S310
                status_code = response.getcode()
                response_text = response.read().decode("utf-8")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            raise SecurityError(f"IntentLock execution failed: {exc.code} {response_text}") from exc
        except URLError as exc:
            raise SecurityError(f"IntentLock execution request failed: {exc}") from exc

        if status_code != 200:
            raise SecurityError(f"IntentLock execution failed: {status_code} {response_text}")

        result: dict[str, Any] = json.loads(response_text)
        return result

    def list_pending_approvals(self) -> dict[str, Any]:
        """List pending HITL approval requests.

        Requires an authenticated bearer token.

        Returns:
            A dictionary containing a list of pending approval requests.

        Raises:
            SecurityError: If the request fails or the user lacks permission.
        """
        url = f"{self.base_url.rsplit('/', 1)[0]}/approval/pending"
        request = Request(  # nosec B310 - _validate_gateway_url restricts scheme to HTTP(S) only  # noqa: S310
            _validate_gateway_url(url),
            headers=self._auth_headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=5) as response:  # nosec B310 - validated HTTP(S) URL above  # nosem  # noqa: S310
                return json.loads(response.read().decode("utf-8"))  # type: ignore[no-any-return]
        except HTTPError as exc:
            raise SecurityError(f"Failed to list approvals: {exc.code}") from exc
        except URLError as exc:
            raise SecurityError(f"Approval list request failed: {exc}") from exc

    def approve_request(self, request_id: str) -> dict[str, Any]:
        """Approve an HITL request.

        Requires an authenticated bearer token with approver role.

        Args:
            request_id: The UUID of the approval request.

        Returns:
            A dictionary confirming the approval.

        Raises:
            SecurityError: If the request fails or the user lacks permission.
        """
        return self._decide_request(request_id, "approve")

    def reject_request(self, request_id: str) -> dict[str, Any]:
        """Reject an HITL request.

        Requires an authenticated bearer token with approver role.

        Args:
            request_id: The UUID of the approval request.

        Returns:
            A dictionary confirming the rejection.

        Raises:
            SecurityError: If the request fails or the user lacks permission.
        """
        return self._decide_request(request_id, "reject")

    def _decide_request(self, request_id: str, action: str) -> dict[str, Any]:
        base = self.base_url.rsplit('/', 1)[0]
        url = f"{base}/approval/{request_id}/{action}"
        request = Request(  # nosec B310 - _validate_gateway_url restricts scheme to HTTP(S) only  # noqa: S310
            _validate_gateway_url(url),
            headers=self._auth_headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:  # nosec B310 - validated HTTP(S) URL above  # nosem  # noqa: S310
                return json.loads(response.read().decode("utf-8"))  # type: ignore[no-any-return]
        except HTTPError as exc:
            raise SecurityError(f"Failed to {action} request: {exc.code}") from exc
        except URLError as exc:
            raise SecurityError(f"{action.capitalize()} request failed: {exc}") from exc


def guard_tool(
    intent_lock_client: IntentLockGuard,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps a tool function with intent verification.

    The decorated function will be checked by IntentLock before execution.
    An execution token is verified and consumed before the wrapped function
    is called, enforcing single-use semantics.

    Args:
        intent_lock_client: An authenticated IntentLockGuard instance.

    Returns:
        A decorator that wraps the target function with intent verification.

    Example:
        ```python
        client = IntentLockGuard(base_url="http://localhost:8000/api/v1/intent/verify")

        @guard_tool(client)
        def query_database(
            query: str, user_prompt: str = "Query DB",
            agent_id: str = "agent-1",
        ) -> str:
            return f"Results for: {query}"
        ```
    """
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
