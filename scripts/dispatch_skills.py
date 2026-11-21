#!/usr/bin/env python3
"""Governed dispatcher for reviewed Shards skills; never evaluates skill-supplied commands."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import stat
import subprocess
import sys
import uuid
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "shards-core"
LOCAL_STATE = ROOT / ".shards" / "state"
REPORTS = ROOT / "reports" / "dispatch"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)

# Only these exact skill identifiers are dispatchable. No user-provided executable paths.
REGISTRY = {
    "shards-repository-health": ("read-only", "plugins/shards-core/scripts/run.py", "repository-health"),
    "shards-skill-audit": ("read-only", "plugins/shards-core/scripts/run.py", "audit-skill"),
    "shards-release-gate": ("read-only", "plugins/shards-core/scripts/run.py", "release-check"),
    "shards-agent-handoff": ("local-write", "plugins/shards-core/scripts/run.py", "handoff"),
    "shards-automation-operator": ("local-tests", "scripts/automate.py", "run"),
    "shards-catalogue-sync": ("read-only", "scripts/catalogue_sync.py", "--check"),
    "shards-skill-dispatch": ("read-only", "scripts/verify_plugins.py", "--check"),
    "shards-a2a-harness": ("read-only", "scripts/shards_agent_harness.py", "a2a-check"),
    "shards-dual-channel": ("read-only", "scripts/shards_agent_harness.py", "dual-channel-check"),
    "shards-subagents": ("read-only", "scripts/shards_agent_harness.py", "subagent-check"),
    "shards-parallel-swarm": ("read-only", "scripts/shards_agent_harness.py", "swarm-check"),
}

HARNESS_SKILLS = frozenset({
    "shards-a2a-harness", "shards-dual-channel",
    "shards-subagents", "shards-parallel-swarm",
})

LOCAL_IMPORTS = {
    "scripts/catalogue_sync.py": ("validate_skills",),
    "scripts/shards_agent_harness.py": ("dispatch_skills",),
    "scripts/verify_plugins.py": ("dispatch_skills",),
}

# The interpreter receives the verified entry point and optional input together.
# Restore script-mode argv and imports without reopening the entry-point pathname.
SOURCE_LAUNCHER = """
import base64
import importlib.abc
import importlib.util
import io
import json
import sys

stream = sys.stdin.buffer
metadata_size = int.from_bytes(stream.read(8), 'big')
bundle = json.loads(stream.read(metadata_size))
sys.stdin = io.TextIOWrapper(io.BytesIO(stream.read()), encoding='utf-8')
sys.argv = sys.argv[1:]
__file__ = sys.argv[0]

class ReviewedModules(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name in bundle['modules']:
            return importlib.util.spec_from_loader(name, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__, encoded = bundle['modules'][module.__name__]
        exec(compile(base64.b64decode(encoded), module.__file__, 'exec'), module.__dict__)

sys.meta_path.insert(0, ReviewedModules())
exec(compile(base64.b64decode(bundle['entry']), __file__, 'exec'), globals())
"""
LAUNCHER_SHA256 = hashlib.sha256(SOURCE_LAUNCHER.encode("utf-8")).hexdigest()

def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _contained(path: Path, directory: Path) -> bool:
    return path.resolve().is_relative_to(directory.resolve())

def _repository_path(relative: str) -> Path:
    path = ROOT / relative
    if not _contained(path, ROOT) or not path.is_file() or path.is_symlink():
        raise ValueError("Trusted executable missing or outside checkout: " + relative)
    return path

def _selected_skill(name: str) -> Path:
    if not NAME.fullmatch(name):
        raise ValueError("Invalid target skill name")
    for base in (CORE / "skills", ROOT / "skills"):
        path = base / name
        if not _contained(path, base) or path.is_symlink():
            continue
        if (path / "SKILL.md").is_file() and not (path / "SKILL.md").is_symlink():
            return path.resolve()
    raise ValueError("Target skill not found")

def _state_file(raw: str, *, must_exist: bool) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError("Explicit checkpoint input and output required")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if path != path.resolve() or not path.is_relative_to(ROOT):
        raise ValueError("Checkpoint traversal or symlink is forbidden")
    if not path.is_relative_to(LOCAL_STATE) or path.suffix.lower() != ".json":
        raise ValueError("Checkpoints must be JSON files inside .shards/state")
    if must_exist and not path.is_file():
        raise ValueError("Checkpoint input missing")
    if not must_exist and path.exists():
        raise ValueError("Checkpoint output already exists")
    return path

def _read_regular_bytes(path: Path) -> bytes:
    """Read a bounded regular file without following links in the checkout path."""
    limit = 2_000_000  # Largest supported checkpoint; consumers enforce their own limits.
    if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent = os.open(ROOT, directory_flags)
        try:
            for part in path.relative_to(ROOT).parts[:-1]:
                child = os.open(part, directory_flags, dir_fd=parent)
                os.close(parent)
                parent = child
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        finally:
            os.close(parent)
        stream = os.fdopen(fd, "rb")
    else:
        # On platforms without relative directory FDs, check before opening and recheck before reading.
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("Dispatch source must be a regular file")
        stream = path.open("rb")
    with stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("Dispatch source must be a bounded regular file")
        if path != path.resolve() or not os.path.samestat(info, path.lstat()):
            raise ValueError("Dispatch source changed during open")
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Dispatch source exceeds byte limit")
        return data

@contextmanager
def _lock_windows_path(path: Path, *, directory: bool):
    """Keep a Windows path entry from being renamed or replaced while published."""
    from ctypes import WinDLL, WinError, get_last_error, wintypes

    kernel = WinDLL("kernel32", use_last_error=True)
    open_file = kernel.CreateFileW
    open_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                          wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    open_file.restype = wintypes.HANDLE
    close_handle = kernel.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    read, list_directory = 0x80000000, 0x0001
    share_read, share_write = 0x1, 0x2
    open_existing = 3
    open_reparse_point, backup_semantics = 0x00200000, 0x02000000
    access = list_directory if directory else read
    # Omit delete sharing for all paths, and omit write sharing for staged files.
    share = share_read | share_write if directory else share_read
    flags = open_reparse_point | (backup_semantics if directory else 0)
    handle = open_file(str(path), access, share, None, open_existing, flags, None)
    if handle == wintypes.HANDLE(-1).value:
        raise WinError(get_last_error())
    try:
        if path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Checkpoint publication refuses Windows reparse points")
        yield
    finally:
        close_handle(handle)

def _publish_checkpoint(path: Path, data: bytes) -> str | None:
    """Publish complete bytes from private staging without overwriting the destination."""
    directory = staging_fd = None
    staging = path.parent / (".handoff-" + uuid.uuid4().hex)
    target = path
    created_directory = created_file = published = False
    cleanup_warning = None
    windows_handles = ExitStack()
    try:
        if {os.open, os.mkdir, os.link, os.unlink, os.rmdir}.issubset(os.supports_dir_fd) and hasattr(os, "O_NOFOLLOW"):
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            directory = os.open(ROOT, flags)
            for part in path.parent.relative_to(ROOT).parts:
                try:
                    child = os.open(part, flags, dir_fd=directory)
                except FileNotFoundError:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=directory)
                    except FileExistsError:
                        pass
                    child = os.open(part, flags, dir_fd=directory)
                os.close(directory)
                directory = child
            staging, target = Path(staging.name), Path(path.name)
        elif os.name == "nt":
            # Anchor every state-directory component before naming the next one.
            parent = ROOT
            windows_handles.enter_context(_lock_windows_path(parent, directory=True))
            for part in path.parent.relative_to(ROOT).parts:
                parent /= part
                parent.mkdir(mode=0o700, exist_ok=True)
                windows_handles.enter_context(_lock_windows_path(parent, directory=True))
            _state_file(str(path), must_exist=False)
        else:
            raise ValueError("Protected checkpoint publication is unavailable on this platform")

        os.mkdir(staging, mode=0o700, dir_fd=directory)
        created_directory = True
        source = staging / "checkpoint.json"
        if directory is not None:
            staging_fd = os.open(staging, flags, dir_fd=directory)
            info = os.fstat(staging_fd)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("Checkpoint staging directory is not private")
            source = Path(source.name)

        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=staging_fd)
        created_file = True
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if directory is None:
            with _lock_windows_path(staging, directory=True), _lock_windows_path(source, directory=False):
                if source.read_bytes() != data:
                    raise ValueError("Staged checkpoint changed before publication")
                os.link(source, target)
        else:
            os.link(source, target, src_dir_fd=staging_fd, dst_dir_fd=directory)
        published = True
    finally:
        try:
            if created_file:
                os.unlink(source, dir_fd=staging_fd)
            if created_directory:
                os.rmdir(staging, dir_fd=directory)
        except OSError:
            if published:
                cleanup_warning = "Checkpoint published. Private staging cleanup failed."
        finally:
            if staging_fd is not None:
                os.close(staging_fd)
            if directory is not None:
                os.close(directory)
            windows_handles.close()
    return cleanup_warning

def _check_descriptor(skill_id: str) -> None:
    skill = CORE / "skills" / skill_id
    descriptor = skill / "SKILL.md"
    if not descriptor.is_file() or descriptor.is_symlink() or (skill / "UPSTREAM.md").exists():
        raise ValueError("Curated skill is missing or untrusted: " + skill_id)
    first = descriptor.read_text(encoding="utf-8")[:1000]
    if not first.startswith("---\n") or ("\nname: " + skill_id + "\n") not in first:
        raise ValueError("Curated skill frontmatter does not match: " + skill_id)

def _read_local_modules(script_path: str) -> dict[str, tuple[Path, bytes]]:
    modules = {}
    for name in LOCAL_IMPORTS.get(script_path, ()):
        path = _repository_path(f"scripts/{name}.py")
        modules[name] = (path, _read_regular_bytes(path))
    return modules

def _module_digests(modules: dict[str, tuple[Path, bytes]]) -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest() for name, (_, data) in modules.items()}

def _source_revision() -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
                           text=True, capture_output=True, timeout=5, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def _plan_fingerprint(plan: dict) -> str:
    """Stable digest of the command and effects the operator actually reviewed."""
    fields = ("skill", "effect", "command", "script_sha256", "launcher_sha256", "module_sha256",
              "commit", "timeout_seconds")
    payload = {key: plan[key] for key in fields}
    if "input_file" in plan:
        payload.update(input_file=plan["input_file"], input_sha256=plan.get("input_sha256"))
    if "output_file" in plan:
        payload["output_file"] = plan["output_file"]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _check_plan_integrity(plan: dict) -> tuple[bytes, dict[str, tuple[Path, bytes]], bytes]:
    """Fail closed if a reviewed plan, trusted script or checkout changed."""
    skill = plan.get("skill")
    if not isinstance(skill, str) or skill not in REGISTRY:
        raise ValueError("Unknown curated skill in execution plan")
    _check_descriptor(skill)
    effect, script_path, operation = REGISTRY[skill]
    if plan.get("effect") != effect:
        raise ValueError("Execution plan effect differs from curated registry")
    expected_timeout = 420 if skill in HARNESS_SKILLS or skill == "shards-automation-operator" else (
        30 if skill == "shards-skill-dispatch" else 180)
    if type(plan.get("timeout_seconds")) is not int or plan["timeout_seconds"] != expected_timeout:
        raise ValueError("Execution plan timeout differs from curated registry")
    if plan.get("approved_by") != "host-required" or plan.get("executed") is not False:
        raise ValueError("Execution plan authorization metadata is invalid")
    script = _repository_path(script_path)
    command = plan.get("command")
    if (not isinstance(command, list) or len(command) < 3 or
            not all(isinstance(arg, str) for arg in command)):
        raise ValueError("Execution plan command is invalid")
    args = command[3:]
    if skill in ("shards-repository-health", "shards-release-gate"):
        expected_args = ["--repo", str(ROOT)]
    elif skill == "shards-skill-audit":
        if len(args) != 2 or args[0] != "--path":
            raise ValueError("Audit command shape is invalid")
        expected_args = ["--path", str(_selected_skill(Path(args[1]).name))]
    elif skill == "shards-agent-handoff":
        _state_file(plan.get("output_file"), must_exist=False)
        expected_args = ["--input", "-"]
    elif skill == "shards-automation-operator":
        if len(args) != 2 or args[0] != "--workflow" or args[1] not in (
                "quick", "weekly", "verify"):
            raise ValueError("Maintenance command shape is invalid")
        expected_args = ["--workflow", args[1]]
    elif skill in HARNESS_SKILLS:
        expected_args = ["--execute"]
    else:
        expected_args = []
    if command != [sys.executable, str(script), operation] + expected_args:
        raise ValueError("Execution plan command differs from curated registry")
    if "output_file" in plan and skill != "shards-agent-handoff":
        raise ValueError("Unexpected output in execution plan")
    source = _read_regular_bytes(script)
    digest = hashlib.sha256(source).hexdigest()
    expected_script = plan.get("script_sha256")
    if not isinstance(expected_script, str) or not hmac.compare_digest(digest, expected_script):
        raise ValueError("Trusted executable changed since planning")
    if plan.get("launcher_sha256") != LAUNCHER_SHA256:
        raise ValueError("Dispatcher launcher changed since planning")
    modules = _read_local_modules(script_path)
    if plan.get("module_sha256") != _module_digests(modules):
        raise ValueError("Trusted Python dependencies changed since planning")
    if not plan.get("commit"):
        raise ValueError("Repository revision unavailable for execution")
    if plan.get("commit") != _source_revision():
        raise ValueError("Repository revision changed since planning")
    claimed = plan.get("plan_sha256")
    actual = _plan_fingerprint(plan)
    if not isinstance(claimed, str) or not hmac.compare_digest(actual, claimed):
        raise ValueError("Execution plan changed since planning")
    if "--input" in expected_args:
        path = _state_file(plan.get("input_file"), must_exist=True)
        data = _read_regular_bytes(path)
        if hashlib.sha256(data).hexdigest() != plan.get("input_sha256"):
            raise ValueError("Reviewed input changed since planning")
        return source, modules, data
    if "input_file" in plan or "input_sha256" in plan:
        raise ValueError("Unexpected input in execution plan")
    return source, modules, b""

def describe(skill_id: str, *, target_skill: str | None = None,
             profile: str = "quick", input_file: str | None = None,
             output_file: str | None = None, allow_local_write: bool = False) -> dict:
    if skill_id not in REGISTRY:
        raise ValueError("Unknown or unapproved skill identifier")
    _check_descriptor(skill_id)
    effect, relative_script, operation = REGISTRY[skill_id]
    script = _repository_path(relative_script)
    cmd = [sys.executable, str(script), operation]
    timeout = 180
    if skill_id == "shards-repository-health" or skill_id == "shards-release-gate":
        cmd.extend(["--repo", str(ROOT)])
    elif skill_id == "shards-skill-audit":
        if target_skill is None:
            raise ValueError("Audit requires --target-skill")
        cmd.extend(["--path", str(_selected_skill(target_skill))])
    elif skill_id == "shards-agent-handoff":
        if not allow_local_write:
            raise ValueError("Handoff requires --allow-local-write")
        cmd.extend(["--input", "-"])
    elif skill_id == "shards-automation-operator":
        if profile not in ("quick", "weekly", "verify"):
            raise ValueError("Only named maintenance profiles can run")
        cmd.extend(["--workflow", profile])
        timeout = 420
    elif skill_id == "shards-skill-dispatch":
        timeout = 30
    elif skill_id in HARNESS_SKILLS:
        cmd.append("--execute")
        timeout = 420
    plan = {"skill": skill_id, "effect": effect, "command": cmd,
            "script_sha256": hashlib.sha256(_read_regular_bytes(script)).hexdigest(),
            "launcher_sha256": LAUNCHER_SHA256,
            "module_sha256": _module_digests(_read_local_modules(relative_script)),
            "commit": _source_revision(), "timeout_seconds": timeout,
            "approved_by": "host-required", "executed": False}
    if "--input" in cmd:
        path = _state_file(input_file, must_exist=True)
        plan.update(input_file=str(path), input_sha256=hashlib.sha256(_read_regular_bytes(path)).hexdigest())
    if skill_id == "shards-agent-handoff":
        plan["output_file"] = str(_state_file(output_file, must_exist=False))
    plan["plan_sha256"] = _plan_fingerprint(plan)
    return plan

def run(plan: dict, *, expect_plan_sha256: str | None = None, executor=None) -> dict:
    plan = dict(plan)
    if isinstance(plan.get("command"), list):
        plan["command"] = plan["command"].copy()
    if isinstance(plan.get("module_sha256"), dict):
        plan["module_sha256"] = plan["module_sha256"].copy()
    source, modules, input_data = _check_plan_integrity(plan)
    requires_pin = ("input_file" in plan or plan["effect"] != "read-only"
                    or plan["skill"] == "shards-release-gate")
    if requires_pin and expect_plan_sha256 is None:
        raise ValueError("This operation requires --expect-plan-sha256 from a reviewed plan")
    if expect_plan_sha256 is not None:
        expected = expect_plan_sha256.lower() if isinstance(expect_plan_sha256, str) else ""
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or not hmac.compare_digest(expected, plan["plan_sha256"]):
            raise ValueError("Reviewed plan SHA-256 does not match current execution plan")
    if executor is None:
        executor = subprocess.run
    env = {key: value for key, value in os.environ.items() if key in
           ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    started = timestamp()
    try:
        command = [sys.executable, "-I", "-B", "-X", "utf8", "-c", SOURCE_LAUNCHER, *plan["command"][1:]]
        bundle = json.dumps({"entry": base64.b64encode(source).decode("ascii"),
                             "modules": {name: (str(path), base64.b64encode(data).decode("ascii"))
                                         for name, (path, data) in modules.items()}}).encode("utf-8")
        payload = len(bundle).to_bytes(8, "big") + bundle + input_data
        proc = executor(command, cwd=str(ROOT), env=env, capture_output=True,
                        timeout=plan["timeout_seconds"], check=False, input=payload)
        stdout_text = proc.stdout.decode("utf-8", "replace") if isinstance(proc.stdout, bytes) else proc.stdout
        stderr_text = proc.stderr.decode("utf-8", "replace") if isinstance(proc.stderr, bytes) else proc.stderr
        stdout = SECRET.sub("[REDACTED]", stdout_text)[-4000:]
        stderr = SECRET.sub("[REDACTED]", stderr_text)[-2000:]
        status = "pass" if proc.returncode == 0 else "fail"
        if plan["skill"] == "shards-release-gate" and proc.returncode == 1:
            try:
                if json.loads(proc.stdout).get("decision") == "HOLD":
                    status = "hold"
            except json.JSONDecodeError:
                pass
        observed = {"status": status, "exit_code": proc.returncode,
                    "stdout_tail": stdout, "stderr_tail": stderr}
        if status == "pass" and "output_file" in plan:
            try:
                report = json.loads(stdout_text)
                if (not isinstance(report, dict) or report.get("workflow") != "handoff"
                        or report.get("status") != "VALIDATED" or not isinstance(report.get("checkpoint"), dict)):
                    raise ValueError("Child did not return a validated checkpoint")
                destination = _state_file(plan["output_file"], must_exist=False)
                warning = _publish_checkpoint(destination, stdout_text.encode("utf-8"))
                if warning:
                    observed["warning"] = warning
            except (OSError, ValueError) as exc:
                observed.update(status="fail", error=str(exc))
    except subprocess.TimeoutExpired:
        observed = {"status": "timeout", "exit_code": None,
                    "error": "Process exceeded timeout"}
    except OSError as exc:
        observed = {"status": "error", "exit_code": None, "error": type(exc).__name__}
    pinned = {key: plan[key] for key in ("input_file", "input_sha256", "output_file") if key in plan}
    return {**pinned, "receipt_id": str(uuid.uuid4()), "skill": plan["skill"],
            "effect": plan["effect"], "commit": plan["commit"],
            "plan_sha256": plan["plan_sha256"],
            "script_sha256": plan["script_sha256"], "launcher_sha256": plan["launcher_sha256"],
            "module_sha256": plan["module_sha256"],
            "command": plan["command"],
            "started_at": started, "finished_at": timestamp(), "executed": True,
            "observation": observed, "production_verified": False}

def persist(receipt: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / (receipt["receipt_id"] + ".json")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    for action in ("plan", "run"):
        s = sub.add_parser(action)
        s.add_argument("--skill", required=True, choices=sorted(REGISTRY))
        s.add_argument("--target-skill")
        s.add_argument("--profile", choices=("quick", "weekly", "verify"), default="quick")
        s.add_argument("--input-file")
        s.add_argument("--output-file")
        s.add_argument("--allow-local-write", action="store_true")
        if action == "run":
            s.add_argument("--execute", action="store_true", help="Explicitly authorize execution")
            s.add_argument("--expect-plan-sha256", metavar="SHA256",
                           help="Fail unless the reviewed plan matches this digest")
            s.add_argument("--save-receipt", action="store_true", help="Write JSON receipt under reports/dispatch")
    args = p.parse_args(argv)
    if args.action == "list":
        print(json.dumps({"skills": [{"name": key, "effect": value[0]}
                                     for key, value in sorted(REGISTRY.items())]}, indent=2))
        return 0
    try:
        plan = describe(args.skill, target_skill=args.target_skill, profile=args.profile,
                        input_file=args.input_file, output_file=args.output_file,
                        allow_local_write=args.allow_local_write)
        if args.action == "plan":
            print(json.dumps(plan, indent=2))
            return 0
        if not args.execute:
            raise ValueError("Run requires --execute; use plan first")
        receipt = run(plan, expect_plan_sha256=args.expect_plan_sha256)
        if args.save_receipt:
            receipt["report_path"] = str(persist(receipt))
        print(json.dumps(receipt, indent=2))
        return 0 if receipt["observation"]["status"] == "pass" else 1
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
