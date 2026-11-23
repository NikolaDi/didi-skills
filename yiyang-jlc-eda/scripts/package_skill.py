"""Package this skill using an explicit source allowlist."""
import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    skill = root / "SKILL.md"
    match = re.search(r"(?m)^name: ([a-z0-9-]+)$", skill.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("SKILL.md must have a name in YAML frontmatter")
    name = match.group(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "dist" / (name + ".skill"))
    args = parser.parse_args()
    target = args.output.resolve()
    sources = [root / f for f in (
        "SKILL.md", "README.md", "THIRD_PARTY_NOTICES.md", "package.json", "package-lock.json", ".gitignore", ".gitattributes",
    )]
    sources += sorted((root / "references").rglob("*.md"))
    sources += sorted(p for p in (root / "scripts").iterdir() if p.suffix in {".py", ".mjs"})
    if any(not p.is_file() for p in sources):
        raise ValueError("Required packaging input is missing")
    if target in sources:
        raise ValueError("Output cannot overwrite a skill source file")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as temp:
        temporary = Path(temp.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in sources:
                info = zipfile.ZipInfo((Path(name) / p.relative_to(root)).as_posix(), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, p.read_bytes())
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None
            assert archive.read(f"{name}/SKILL.md") == skill.read_bytes()
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(json.dumps({"output": str(target), "files": len(sources), "bytes": target.stat().st_size,
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
