import re
from functools import lru_cache
from importlib.resources import files

import yaml
from jinja2 import Environment, StrictUndefined


@lru_cache
def load_plugin(case_type: str) -> tuple[dict, list[dict]]:
    root = plugin_folder(case_type)
    return (
        yaml.safe_load(root.joinpath("rules.yaml").read_text(encoding="utf-8")),
        yaml.safe_load(root.joinpath("checklist.yaml").read_text(encoding="utf-8")),
    )


def plugin_folder(case_type: str):
    if not re.fullmatch(r"[a-z][a-z_]+", case_type):
        raise ValueError("Invalid case plugin identifier")
    return files(f"app.case_types.{case_type}")


def render_notice(case_type: str, kind: str, **values) -> str:
    rules, _ = load_plugin(case_type)
    if kind not in rules["notice_kinds"]:
        raise ValueError("Notice type is unavailable for this case")
    source = plugin_folder(case_type).joinpath("templates", f"{kind}.txt").read_text(encoding="utf-8")
    return Environment(undefined=StrictUndefined).from_string(source).render(**values)
