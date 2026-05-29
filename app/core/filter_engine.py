import re


class FilterEngine:
    def __init__(self):
        self._pattern: re.Pattern | None = None

    def compile(self, pattern: str, is_regex: bool = True):
        self._pattern = None
        if not pattern.strip():
            return
        try:
            if is_regex:
                self._pattern = re.compile(pattern)
            else:
                self._pattern = re.compile(re.escape(pattern))
        except re.error:
            pass

    def apply(self, lines: list[str]) -> list[str]:
        if self._pattern is None:
            return lines
        return [self._pattern.sub("", line) for line in lines]

    @property
    def active(self) -> bool:
        return self._pattern is not None
