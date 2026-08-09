import time
from pathlib import Path

from sdk.intentlock import IntentLockGuard, SecurityError, guard_tool


LOG_PATH = Path("logs") / "audit_trail.jsonl"
intent_lock = IntentLockGuard()


@guard_tool(intent_lock)
def execute_sql(query: str, user_prompt: str, agent_id: str) -> str:
    print(f"Executing SQL query: {query}")
    return "Query executed successfully."


@guard_tool(intent_lock)
def transfer_money(amount: float, recipient: str, user_prompt: str, agent_id: str) -> str:
    print(f"Transferring ${amount:.2f} to {recipient}")
    return "Transfer completed."


def main() -> None:
    print("--- IntentLock Demo: Legitimate Request ---")
    try:
        result = execute_sql(
            "SELECT * FROM sales;",
            user_prompt="Fetch Q3 Sales Report",
            agent_id="agent-legit-001",
        )
        print(result)
    except SecurityError as exc:
        print(f"Blocked: {exc}")

    print("\nWaiting for 1 second before the next scenario...\n")
    time.sleep(1)

    print("--- IntentLock Demo: Prompt Injection Attack ---")
    try:
        execute_sql(
            "DROP TABLE users;",
            user_prompt="Fetch Q3 Sales Report",
            agent_id="agent-evil-001",
        )
    except SecurityError as exc:
        print(f"Blocked destructive SQL: {exc}")

    print("\n--- IntentLock Demo: Unauthorized Transfer ---")
    try:
        transfer_money(
            50000.0,
            "malicious-vendor",
            user_prompt="Transfer no more than $100",
            agent_id="agent-evil-002",
        )
    except SecurityError as exc:
        print(f"Blocked unauthorized transfer: {exc}")

    print("\nVerifying audit trail records...")
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as handle:
            entries = [line.strip() for line in handle if line.strip()]
        print(f"Found {len(entries)} audit event(s) in {LOG_PATH}")
        for entry in entries[-3:]:
            print(entry)
    else:
        print(f"Audit trail file not found at {LOG_PATH}")


if __name__ == "__main__":
    main()
