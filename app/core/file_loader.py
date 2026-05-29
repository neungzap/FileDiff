from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

BINARY_CHECK_SIZE = 8192
TEXT_EXTENSIONS = {
    ".txt", ".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".ini", ".cfg", ".toml", ".sh", ".bash", ".zsh", ".fish", ".md", ".rst",
    ".html", ".htm", ".xml", ".css", ".scss", ".sass", ".less",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".go", ".rs", ".rb", ".php",
    ".sql", ".log", ".csv", ".tsv", ".diff", ".patch", ".env", ".gitignore",
    ".dockerfile", ".makefile", ".r", ".swift", ".m",
}


@dataclass
class FileContent:
    lines: list[str]
    encoding: str
    line_ending: str
    path: str
    size_bytes: int


class BinaryFileError(Exception):
    pass


class FileLoadError(Exception):
    pass


def _is_binary(data: bytes) -> bool:
    return b"\x00" in data


def _detect_encoding(path: str) -> str:
    try:
        from charset_normalizer import from_path
        results = from_path(path)
        best = results.best()
        if best is not None:
            return str(best.encoding)
    except Exception:
        pass
    return "utf-8"


def _detect_line_ending(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    if crlf >= lf and crlf >= cr:
        return "CRLF"
    if cr > lf:
        return "CR"
    return "LF"


def load_file(path: str, encoding: str | None = None) -> FileContent:
    p = Path(path)
    if not p.exists():
        raise FileLoadError(f"File not found: {path}")

    size = p.stat().st_size

    # Binary sniff
    with open(path, "rb") as f:
        header = f.read(BINARY_CHECK_SIZE)

    if _is_binary(header):
        suffix = p.suffix.lower()
        if suffix not in TEXT_EXTENSIONS:
            raise BinaryFileError(f"Binary file detected — cannot display in text mode: {path}")

    # Encoding detection
    if encoding is None:
        encoding = _detect_encoding(path)

    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            raw = f.read()
    except (UnicodeDecodeError, LookupError) as e:
        raise FileLoadError(f"Cannot decode file with encoding {encoding}: {e}")

    line_ending = _detect_line_ending(raw)

    # Normalize line endings
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Split preserving empty lines; strip trailing newline to avoid phantom last line
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    return FileContent(
        lines=lines,
        encoding=encoding,
        line_ending=line_ending,
        path=str(p.resolve()),
        size_bytes=size,
    )
