"""Benchmark task input seam (SPEC: benchmark-before-material-projection).

Derived task records (``data/derived/tasks_full/T##.json``) carry the
ASSIGNMENT prompt in ``material`` and the real source document to be revised
in ``before``. Every benchmark execution path must:

- project ``before`` as the article body (material file / WritingContext),
- keep ``material`` as the assignment intent in the prompt,
- fail loudly BEFORE any model call when ``before`` is unusable.

Regression: T01's ``material`` is a 144-char instruction ("Revise the BEFORE
document...") while the body is the 4498-char ``before`` text. Runners that
passed ``material`` as the body saved metadiscourse about the task, not a
revision — yet artifact existence was still recorded as success.
"""

from __future__ import annotations


def resolve_task_inputs(full: dict, task_id: str) -> dict:
    """Split a derived task record into assignment + BEFORE document.

    Raises ValueError naming the task and the missing field; callers invoke
    this before composing the agent or calling the model, so a task with no
    usable body can never produce a success artifact.
    """
    assignment = full.get("material")
    before = full.get("before")
    if not isinstance(assignment, str) or not assignment.strip():
        raise ValueError(
            f"{task_id}: 'material' (assignment) missing or empty — the task "
            "record has no assignment intent"
        )
    if not isinstance(before, str) or not before.strip():
        raise ValueError(
            f"{task_id}: 'before' (BEFORE document) missing or empty — a "
            "revision run needs the real source body; refusing to start"
        )
    return {"assignment": assignment, "before_text": before}
