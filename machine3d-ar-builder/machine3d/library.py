"""Persistent, versioned and conservative registry for validated v2 machine blueprints.

A template is reusable only after a real Blender build and export passed quality
checks. This is *pipeline* validation, NOT proof of engineering correctness.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import json
import os
import re
import shutil
import tempfile

from .blueprints import validate_blueprint
from .validation import validate_export, validate_metadata


def _default_library() -> Path:
    """Keep learned assets OUTSIDE the replaceable skill folder on Cursor projects."""
    skill_root = Path(__file__).resolve().parent.parent
    if skill_root.parent.name == "skills" and skill_root.parent.parent.name == ".cursor":
        return skill_root.parent.parent.parent / ".machine3d" / "templates"
    return Path.home() / ".machine3d" / "templates"


DEFAULT_LIBRARY = _default_library()
_ALLOWED_ID = re.compile(r"[a-z][a-z0-9_]*\Z")


def normalize_request(value: str) -> str:
    """Conservative canonical request; removes presentation modifiers, not machine subtypes."""
    text = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    # Only strip phrases introducing presentation needs, not mechanism attributes.
    text = re.split(r"\b(?:with|for my|for an|for the|including|showing)\b", text, maxsplit=1)[0]
    text = re.sub(r"^(?:please )?(?:(?:create|build|make|generate|model|design|render) )(?:me )?(?:an? |the )?", "", text)
    text = re.sub(r"^(?:(?:interactive|realistic|detailed|educational|animated|3d) )+", "", text)
    return " ".join(text.split())


def _digest(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


@contextmanager
def _library_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    file = root / ".registry.lock"
    with file.open("a+b") as handle:
        # fcntl is available on Mac and Linux, the supported build platforms.
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class TemplateLibrary:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or os.environ.get("MACHINE3D_TEMPLATE_LIBRARY", DEFAULT_LIBRARY)).expanduser().resolve()

    def _entry_dir(self, machine_id: str) -> Path:
        if not _ALLOWED_ID.fullmatch(machine_id):
            raise ValueError("Unsafe template id")
        return self.root / machine_id

    def entries(self) -> list[dict]:
        """Read latest entries; ignore missing/invalid/corrupted records."""
        result = []
        if not self.root.is_dir():
            return result
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or not _ALLOWED_ID.fullmatch(directory.name):
                continue
            try:
                record = json.loads((directory / "latest.json").read_text(encoding="utf-8"))
                version = record["version"]
                if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[0-9a-f]{12}", version):
                    continue
                source = directory / "versions" / version / "blueprint.json"
                contents = source.read_bytes()
                if _digest(contents) != record["sha256"]:
                    continue
                bp = json.loads(contents)
                validate_blueprint(bp)
                if bp["id"] != directory.name:
                    continue
                result.append({**record, "blueprintPath": str(source)})
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
        return result

    def match(self, prompt: str) -> dict | None:
        requested = normalize_request(prompt)
        if not requested:
            return None
        candidates = []
        for record in self.entries():
            aliases = record.get("aliases", [])
            if requested in aliases:
                candidates.append(record)
        # Do not silently use an ambiguous template.
        if len(candidates) > 1:
            raise ValueError("Multiple learned templates match the request; specify a unique machine type")
        return candidates[0] if candidates else None

    def load(self, record: dict) -> dict:
        path = Path(record["blueprintPath"]).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Template path is outside library")
        blob = path.read_bytes()
        if _digest(blob) != record["sha256"]:
            raise ValueError("Template blueprint digest mismatch")
        data = json.loads(blob)
        validate_blueprint(data)
        return data

    def promote(self, blueprint: dict, output: Path, *, prompt: str | None = None,
                aliases: Iterable[str] = ()) -> dict:
        """Only promote an actually built and validated v2 blueprint.

        This gate requires Blender execution evidence plus a structurally valid USDZ;
        it is not a physical simulation, CAD inspection or on-device AR test.
        """
        validate_blueprint(blueprint)
        output = Path(output).expanduser().resolve()
        checks = [validate_metadata(output), validate_export(output)]
        try:
            blender_check = json.loads((output / "blender_validation.json").read_text(encoding="utf-8"))
            export_check = json.loads((output / "export_validation.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("Promotion requires Blender and export validation reports") from exc
        if any(not c["passed"] for c in checks) or not blender_check.get("passed") or not export_check.get("passed"):
            raise ValueError("Promotion blocked: metadata, Blender or export validation failed")
        if blender_check.get("components") != len(blueprint["components"]):
            raise ValueError("Promotion blocked: Blender component count mismatch")
        actual = json.loads((output / "blueprint.json").read_text(encoding="utf-8"))
        if actual != blueprint:
            raise ValueError("Promotion blocked: provided blueprint does not match built blueprint")
        if blueprint.get("generatorDependencies"):
            raise ValueError("Custom generator dependencies need a separately versioned implementation; auto-promotion is not safe")
        # Avoid matching overly generic aliases by accident: only explicit input and machine name.
        alias_values = [blueprint["displayName"], *aliases]
        if prompt:
            alias_values.append(prompt)
        new_aliases = sorted({a for raw in alias_values if (a := normalize_request(raw))})
        if not new_aliases:
            raise ValueError("Template has no usable aliases")
        payload = _json_bytes(blueprint)
        hexdigest = _digest(payload)
        entry = self._entry_dir(blueprint["id"])
        with _library_lock(self.root):
            latest_path = entry / "latest.json"
            old = None
            if latest_path.exists():
                old = json.loads(latest_path.read_text(encoding="utf-8"))
            merged_aliases = sorted(set(new_aliases + (old.get("aliases", []) if old else [])))
            if old and old["sha256"] == hexdigest:
                old["aliases"] = merged_aliases
                self._atomic_write(latest_path, _json_bytes(old))
                return {**old, "action": "reused_existing_version"}
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            version = f"{timestamp}_{hexdigest[:12]}"
            destination = entry / "versions" / version
            if destination.exists():
                raise ValueError("Template version already exists with unexpected state")
            destination.mkdir(parents=True, exist_ok=False)
            (destination / "blueprint.json").write_bytes(payload)
            for filename in ("machine.json", "animation_spec.json", "geometry_spec.json",
                             "plan_report.json", "blender_validation.json", "export_validation.json"):
                src = output / filename
                if src.is_file():
                    shutil.copy2(src, destination / filename)
            # Do not duplicate large generated assets in the skill's source tree.
            record = {
                "id": blueprint["id"], "displayName": blueprint["displayName"],
                "version": version, "sha256": hexdigest,
                "aliases": merged_aliases,
                "validationLevel": "blender-and-export-pipeline-validated",
                "engineeringVerified": False, "realityKitDeviceVerified": False,
                "componentCount": len(blueprint["components"]),
                "promotedAt": datetime.now(timezone.utc).isoformat(),
                "sourceOutput": str(output),
                "previousVersion": old["version"] if old else None,
            }
            (destination / "manifest.json").write_bytes(_json_bytes(record))
            self._atomic_write(latest_path, _json_bytes(record))
            return {**record, "action": "created_version"}

    @staticmethod
    def _atomic_write(target: Path, data: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
