import os
import yaml
import structlog
from functools import lru_cache
from pathlib import Path

logger = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


@lru_cache(maxsize=1)
def load_candidate_profile() -> dict:
    path = CONFIG_DIR / "candidate_profile.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_system_config() -> dict:
    path = CONFIG_DIR / "system_config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_all_target_roles() -> list[str]:
    profile = load_candidate_profile()
    roles = []
    for category in profile.get("target_roles", {}).values():
        roles.extend(category)
    return roles


def get_all_skills() -> list[str]:
    profile = load_candidate_profile()
    skills = []
    for category in profile.get("skills", {}).values():
        for skill in category:
            skills.append(skill["name"])
    return skills


def get_enabled_locations() -> dict:
    profile = load_candidate_profile()
    return profile.get("location_preferences", {})


def get_llm_config(task: str) -> dict:
    config = load_system_config()
    llm = config.get("llm", {})
    task_config = llm.get(task, {})
    return {
        "model": task_config.get("model", llm.get("primary_model")),
        "temperature": task_config.get("temperature", 0.2),
        "max_tokens": task_config.get("max_tokens", 2048),
        "fallback_model": llm.get("fallback_model"),
    }
