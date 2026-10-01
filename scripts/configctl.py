#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform as py_platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "configs" / "catalog.yaml"
PROFILES_DIR = ROOT / "profiles"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = yaml.safe_load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def detect_platform() -> str:
    if os.name == "nt":
        return "windows"
    if py_platform.system().lower() == "linux":
        try:
            if "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower():
                return "wsl"
        except OSError:
            pass
        return "linux"
    raise RuntimeError(f"unsupported host platform: {py_platform.system()}")


def expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def catalog() -> dict[str, Any]:
    doc = load_yaml(CATALOG_PATH)
    if doc.get("schema_version") != 1:
        raise ValueError("configs/catalog.yaml: schema_version must be 1")
    configs = doc.get("configs")
    if not isinstance(configs, dict) or not configs:
        raise ValueError("configs/catalog.yaml: configs must be a non-empty mapping")
    return configs


def profile(name: str) -> dict[str, Any]:
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"unknown profile: {name}")
    doc = load_yaml(path)
    if doc.get("schema_version") != 1:
        raise ValueError(f"{path}: schema_version must be 1")
    if doc.get("profile") != name:
        raise ValueError(f"{path}: profile must equal {name!r}")
    return doc


def validate_all() -> list[str]:
    errors: list[str] = []
    try:
        configs = catalog()
    except Exception as exc:
        return [str(exc)]

    required_config_keys = {"repository", "ref", "platforms", "checkout", "install"}
    for config_id, cfg in configs.items():
        if not isinstance(cfg, dict):
            errors.append(f"config {config_id}: expected mapping")
            continue
        missing = required_config_keys - set(cfg)
        if missing:
            errors.append(f"config {config_id}: missing {sorted(missing)}")
            continue
        platforms = cfg.get("platforms")
        if not isinstance(platforms, list) or not platforms:
            errors.append(f"config {config_id}: platforms must be a non-empty list")
            continue
        for host_platform in platforms:
            if host_platform not in {"linux", "wsl", "windows"}:
                errors.append(f"config {config_id}: unsupported platform {host_platform!r}")
            if host_platform not in cfg.get("checkout", {}):
                errors.append(f"config {config_id}: missing checkout path for {host_platform}")
            if host_platform not in cfg.get("install", {}):
                errors.append(f"config {config_id}: missing install action for {host_platform}")

    profile_names: set[str] = set()
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        try:
            doc = load_yaml(path)
            name = doc.get("profile")
            if not isinstance(name, str) or not name:
                errors.append(f"{path}: profile must be a non-empty string")
                continue
            if name in profile_names:
                errors.append(f"duplicate profile id: {name}")
            profile_names.add(name)
            if doc.get("schema_version") != 1:
                errors.append(f"{path}: schema_version must be 1")
            platforms = doc.get("platforms")
            if not isinstance(platforms, list) or not platforms:
                errors.append(f"{path}: platforms must be a non-empty list")
            selected = doc.get("configs")
            if not isinstance(selected, list) or not selected:
                errors.append(f"{path}: configs must be a non-empty list")
                continue
            if len(selected) != len(set(selected)):
                errors.append(f"{path}: configs must not contain duplicates")
            for config_id in selected:
                if config_id not in configs:
                    errors.append(f"{path}: unknown config {config_id!r}")
                    continue
                supported = set(configs[config_id]["platforms"])
                for host_platform in platforms or []:
                    if host_platform not in supported:
                        errors.append(
                            f"{path}: config {config_id!r} does not support profile platform {host_platform!r}"
                        )
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return errors


def plan_rows(profile_name: str, host_platform: str) -> list[dict[str, str]]:
    configs = catalog()
    prof = profile(profile_name)
    if host_platform not in prof["platforms"]:
        raise ValueError(
            f"profile {profile_name!r} supports {prof['platforms']}, not {host_platform!r}"
        )
    rows = []
    for config_id in prof["configs"]:
        cfg = configs[config_id]
        target = expand_path(cfg["checkout"][host_platform])
        installer = cfg["install"][host_platform]
        rows.append(
            {
                "id": config_id,
                "repository": cfg["repository"],
                "ref": str(cfg["ref"]),
                "target": str(target),
                "install": "none" if installer is None else str(installer),
            }
        )
    return rows


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_git_checkout(row: dict[str, str]) -> Path:
    target = Path(row["target"])
    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"refusing to replace non-Git path: {target}")
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=target, check=True, text=True, capture_output=True
        ).stdout.strip()
        if dirty:
            raise RuntimeError(f"refusing to update dirty checkout: {target}")
        run(["git", "fetch", "origin", "--prune"], cwd=target)
        run(["git", "checkout", row["ref"]], cwd=target)
        run(["git", "pull", "--ff-only", "origin", row["ref"]], cwd=target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--branch", row["ref"], "--single-branch", row["repository"], str(target)])
    return target


def apply_profile(profile_name: str, host_platform: str) -> None:
    rows = plan_rows(profile_name, host_platform)
    for row in rows:
        print(f"==> {row['id']}: {row['repository']} -> {row['target']}")
        target = ensure_git_checkout(row)
        installer = row["install"]
        if installer == "none":
            continue
        if installer == "manual":
            print(f"    manual install required for {row['id']}; checkout is ready")
            continue
        run(["bash", "-lc", installer], cwd=target)


def command_validate(_: argparse.Namespace) -> int:
    errors = validate_all()
    if errors:
        print("personal-config validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1
    print("personal-config validation: OK")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    host_platform = args.platform or detect_platform()
    for row in plan_rows(args.profile, host_platform):
        print(
            f"{row['id']}: repo={row['repository']} ref={row['ref']} "
            f"target={row['target']} install={row['install']}"
        )
    return 0


def command_apply(args: argparse.Namespace) -> int:
    host_platform = args.platform or detect_platform()
    apply_profile(args.profile, host_platform)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Personal configuration profile orchestrator")
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.set_defaults(func=command_validate)
    for name, func in (("plan", command_plan), ("apply", command_apply)):
        sp = sub.add_parser(name)
        sp.add_argument("profile")
        sp.add_argument("--platform", choices=["linux", "wsl", "windows"])
        sp.set_defaults(func=func)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
