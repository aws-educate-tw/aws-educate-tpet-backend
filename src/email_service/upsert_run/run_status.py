from run_status_enum import RunStatus
from run_type_enum import RunType


def get_initial_run_status(run_type: str, scheduled_at: str | None) -> str:
    """Return the initial status for a run entering the send pipeline."""
    if run_type == RunType.WEBHOOK.value:
        return RunStatus.ACTIVE.value
    if scheduled_at is not None:
        return RunStatus.SCHEDULED.value
    return RunStatus.SENDING.value
