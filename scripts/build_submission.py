"""Build an allowlisted source ZIP with file hashes, excluding local state."""

from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ("README.md", "pyproject.toml", "requirements.txt", "requirements-lock.txt", ".env.example", ".gitignore")
FOLDERS = {"src/finnie": {".py"}, "tests": {".py"}, "scripts": {".py"},
           "articles": {".md", ".json"}, "samples": {".csv", ".json"},
           "evaluation": {".json", ".md"}, "docs": {".md"}}
ARCHIVE_ROOT = "finnie-submission"
LOCAL_ONLY_FILES = {"AGENTS.md", "docs/demo-video.md"}


def collect_files(root: Path) -> list[Path]:
    """Allow only documented artifacts; never walk .env, venv, or cache folders."""
    files = []
    for name in ROOT_FILES:
        path = root/name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Required submission file is missing or linked: {name}")
        files.append(path)
    for folder, suffixes in FOLDERS.items():
        for path in (root/folder).rglob('*'):
            relative = path.relative_to(root)
            if relative.as_posix() in LOCAL_ONLY_FILES:
                continue
            if any(part.startswith('.') or part == '__pycache__' for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"Linked submission path is not allowed: {relative}")
            if path.is_file() and path.suffix in suffixes:
                files.append(path)
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def build_submission(root: Path = ROOT, output: Path | None = None) -> Path:
    output = output or root/'dist/finnie-submission.zip'
    output.parent.mkdir(exist_ok=True, parents=True)
    records = []
    contents = []
    for path in collect_files(root):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        # Do not echo matching content if a credential-like literal is detected.
        if re.search(rb'\bsk-[A-Za-z0-9_-]{20,}',data):
            raise ValueError(f"Credential-like content detected in {relative}; review before packaging")
        records.append(dict(path=relative, bytes=len(data), sha256=sha256(data).hexdigest()))
        contents.append((relative,data))
    manifest=dict(format_version=1,files=records,
                  scope="Allowlisted source distribution; secrets, environments, caches, reports and course reference files excluded")
    temporary=output.with_suffix('.zip.tmp')
    try:
        with ZipFile(temporary,'w',compression=ZIP_DEFLATED) as archive:
            for relative,data in contents:
                archive.writestr(f'{ARCHIVE_ROOT}/{relative}',data)
            archive.writestr(f'{ARCHIVE_ROOT}/MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('Archive integrity check failed')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    digest=sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n')
    print(f'Built {output.name}: {len(records)} source files, {output.stat().st_size:,} bytes')
    return output


if __name__=='__main__':
    build_submission()
