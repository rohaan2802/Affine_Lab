"""Small, packaged synthetic corpus derived from the verified baseline."""

from functools import lru_cache
from importlib.resources import files
import json


@lru_cache(maxsize=1)
def load_cases() -> tuple[dict, ...]:
    return tuple(
        json.loads(
            files("affine_lab")
            .joinpath("resources/demo_cases.json")
            .read_text(encoding="utf-8")
        )
    )


def get_case(case_id: int) -> dict:
    if type(case_id) is not int or not 1 <= case_id <= len(load_cases()):
        raise ValueError("case must be an integer from 1 to 5")
    return dict(load_cases()[case_id - 1])


def public_cases() -> list[dict]:
    return [
        {k: c[k] for k in ("id", "username", "mood", "concern")} for c in load_cases()
    ]
