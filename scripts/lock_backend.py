"""Pin the tested runtime dependency closure, including Windows and Linux requirements."""

import importlib.metadata as metadata
import tomllib
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root = Path(__file__).resolve().parents[1]
project = tomllib.loads((root / "backend/pyproject.toml").read_text())
queue = [Requirement(value) for value in project["project"]["dependencies"]]
seen = set()
versions = {}
while queue:
    requirement = queue.pop()
    key = canonicalize_name(requirement.name), tuple(sorted(requirement.extras))
    if key in seen:
        continue
    seen.add(key)
    distribution = metadata.distribution(requirement.name)
    versions[key[0]] = distribution.version
    for value in distribution.requires or []:
        child = Requirement(value)
        environments = []
        for system, platform, os_name in (("Windows", "win32", "nt"), ("Linux", "linux", "posix")):
            for extra in requirement.extras or {""}:
                environments.append({**default_environment(), "platform_system": system, "sys_platform": platform, "os_name": os_name, "extra": extra})
        if child.marker is None or any(child.marker.evaluate(env) for env in environments):
            queue.append(child)
content = "# Runtime versions verified on Python 3.12. Regenerate with scripts/lock_backend.py.\n"
content += "\n".join(f"{name}=={version}" for name, version in sorted(versions.items())) + "\n"
(root / "backend/requirements.lock").write_text(content, encoding="utf-8")
print(f"Pinned {len(versions)} runtime distributions")
