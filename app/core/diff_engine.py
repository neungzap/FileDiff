from __future__ import annotations
from dataclasses import dataclass, field
import difflib
from .filter_engine import FilterEngine

ROW_EQUAL = "equal"
ROW_ADDED = "added"
ROW_DELETED = "deleted"
ROW_MODIFIED = "modified"
ROW_PHANTOM = "phantom"


@dataclass
class DiffResult:
    left_lines: list[str] = field(default_factory=list)
    right_lines: list[str] = field(default_factory=list)
    left_row_types: dict[int, str] = field(default_factory=dict)
    right_row_types: dict[int, str] = field(default_factory=dict)
    left_char_ranges: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    right_char_ranges: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    diff_row_indices: list[int] = field(default_factory=list)
    left_line_numbers: list[int | None] = field(default_factory=list)
    right_line_numbers: list[int | None] = field(default_factory=list)


def _char_diff(a: str, b: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    a_ranges, b_ranges = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            a_ranges.append((i1, i2))
        if tag in ("replace", "insert"):
            b_ranges.append((j1, j2))
    return a_ranges, b_ranges


def compute_diff(
    left_lines: list[str],
    right_lines: list[str],
    filter_engine: FilterEngine | None = None,
) -> DiffResult:
    result = DiffResult()

    # Apply filter to a copy for diffing; keep originals for display
    if filter_engine and filter_engine.active:
        left_filtered = filter_engine.apply(left_lines)
        right_filtered = filter_engine.apply(right_lines)
    else:
        left_filtered = left_lines
        right_filtered = right_lines

    matcher = difflib.SequenceMatcher(None, left_filtered, right_filtered, autojunk=False)
    opcodes = matcher.get_opcodes()

    out_left: list[str] = []
    out_right: list[str] = []
    left_types: dict[int, str] = {}
    right_types: dict[int, str] = {}
    left_char: dict[int, list[tuple[int, int]]] = {}
    right_char: dict[int, list[tuple[int, int]]] = {}
    diff_rows: list[int] = []
    left_lnums: list[int | None] = []
    right_lnums: list[int | None] = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1):
                row = len(out_left)
                out_left.append(left_lines[i1 + k])
                out_right.append(right_lines[j1 + k])
                left_lnums.append(i1 + k + 1)
                right_lnums.append(j1 + k + 1)

        elif tag == "replace":
            left_block = list(range(i1, i2))
            right_block = list(range(j1, j2))
            max_len = max(len(left_block), len(right_block))
            for k in range(max_len):
                row = len(out_left)
                if k < len(left_block):
                    li = left_block[k]
                    out_left.append(left_lines[li])
                    left_types[row] = ROW_MODIFIED
                    left_lnums.append(li + 1)
                else:
                    out_left.append("")
                    left_types[row] = ROW_PHANTOM
                    left_lnums.append(None)

                if k < len(right_block):
                    ri = right_block[k]
                    out_right.append(right_lines[ri])
                    right_types[row] = ROW_MODIFIED
                    right_lnums.append(ri + 1)
                else:
                    out_right.append("")
                    right_types[row] = ROW_PHANTOM
                    right_lnums.append(None)

                diff_rows.append(row)

                # Char-level diff only for paired modified lines
                if k < len(left_block) and k < len(right_block):
                    a_ranges, b_ranges = _char_diff(
                        left_lines[left_block[k]], right_lines[right_block[k]]
                    )
                    if a_ranges:
                        left_char[row] = a_ranges
                    if b_ranges:
                        right_char[row] = b_ranges

        elif tag == "delete":
            for k in range(i2 - i1):
                row = len(out_left)
                out_left.append(left_lines[i1 + k])
                out_right.append("")
                left_types[row] = ROW_DELETED
                right_types[row] = ROW_PHANTOM
                left_lnums.append(i1 + k + 1)
                right_lnums.append(None)
                diff_rows.append(row)

        elif tag == "insert":
            for k in range(j2 - j1):
                row = len(out_left)
                out_left.append("")
                out_right.append(right_lines[j1 + k])
                left_types[row] = ROW_PHANTOM
                right_types[row] = ROW_ADDED
                left_lnums.append(None)
                right_lnums.append(j1 + k + 1)
                diff_rows.append(row)

    result.left_lines = out_left
    result.right_lines = out_right
    result.left_row_types = left_types
    result.right_row_types = right_types
    result.left_char_ranges = left_char
    result.right_char_ranges = right_char
    result.diff_row_indices = sorted(set(diff_rows))
    result.left_line_numbers = left_lnums
    result.right_line_numbers = right_lnums
    return result
