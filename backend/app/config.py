"""CareLoop configuration.

Every secret comes from the environment — nothing is hard-coded.
Copy ../.env.example to ../.env and fill in what you need.
"""
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# "bedrock" = Amazon Bedrock (Nova) via boto3. "demo" = built-in deterministic
# demo-mode agent that uses the exact same tools (no cloud needed).
LLM_PROVIDER = os.getenv("CARELOOP_LLM_PROVIDER", "demo").lower()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# Model used for the AWS Builder mini-challenge integration.
BEDROCK_MODEL_ID = os.getenv("CARELOOP_BEDROCK_MODEL", "amazon.nova-lite-v1:0")

_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "careloop.db")
DB_PATH = os.getenv("CARELOOP_DB_PATH", _default_db)

# Minutes after a scheduled dose before a missed dose escalates to caregivers.
GRACE_MINUTES = _int("CARELOOP_GRACE_MINUTES", 30)
# How often the reminder scheduler ticks (seconds).
SCHEDULER_INTERVAL_SECONDS = _int("CARELOOP_SCHEDULER_INTERVAL", 30)
# Minutes a snoozed dose waits before reminding again.
SNOOZE_MINUTES = _int("CARELOOP_SNOOZE_MINUTES", 15)
