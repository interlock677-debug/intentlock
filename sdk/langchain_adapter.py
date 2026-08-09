import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class IntentLockLangChainTool:
    """Wraps a LangChain tool or callable with IntentLock verification."""

    def __init__(self, tool: Callable[..., Any], base_url: str = "http://127.0.0.1:8000/api/v1/intent/verify") -> None:
        self._tool = tool
        self.base_url = base_url
        self.tool_name = self._resolve_tool_name(tool)

    @staticmethod
    def _resolve_tool_name(tool: Callable[..., Any]) -> str:
        if hasattr(tool, "name") and isinstance(getattr(tool, "name"), str):
            return getattr(tool, "name")
        if hasattr(tool, "__name__") and isinstance(getattr(tool, "__name__"), str):
            return getattr(tool, "__name__")
        return tool.__class__.__name__

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        user_prompt = kwargs.get("user_prompt", "Agent tool execution request")
        agent_id = kwargs.get("agent_id", "agent-000")

        tool_arguments = {}
        if args:
            tool_arguments["args"] = [*args]
        tool_arguments.update(
            {
                key: value
                for key, value in kwargs.items()
                if key not in {"user_prompt", "agent_id"}
            }
        )

        payload = {
            "user_prompt": user_prompt,
            "agent_id": agent_id,
            "reasoning_step": f"Execute {self.tool_name}",
            "proposed_tool": self.tool_name,
            "tool_arguments": tool_arguments,
        }

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=5) as response:
                status_code = response.getcode()
                response_text = response.read().decode("utf-8")
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8") if hasattr(exc, "read") else str(exc)
            return self._blocked_response(response_text)
        except URLError as exc:
            raise RuntimeError(f"IntentLock request failed: {exc}") from exc

        if status_code != 200:
            return self._blocked_response(response_text)

        return self._tool(*args, **kwargs)

    def _blocked_response(self, response_text: str) -> str:
        reason = self._extract_reason(response_text)
        return f"ACTION BLOCKED BY SECURITY POLICY: {reason}"

    @staticmethod
    def _extract_reason(response_text: str) -> str:
        try:
            payload = json.loads(response_text)
            detail = payload.get("detail")
            if isinstance(detail, str) and detail:
                return detail
        except json.JSONDecodeError:
            pass
        return response_text.strip()

    def __getattr__(self, item: str) -> Any:
        return getattr(self._tool, item)
