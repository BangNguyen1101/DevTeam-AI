"""Deterministic security scan of generated code.

LLM reviewers (especially small/free models) notice issues without fixing them;
these rules give the review step a ground truth it is re-checked against.
Patterns are intentionally simple and high-signal for the MVP project contract
(FastAPI backend + vanilla JS frontend).
"""

import re
from dataclasses import asdict, dataclass
from pathlib import Path

# Any innerHTML/outerHTML assignment is a sink unless the right-hand side is a fully static
# literal ('' / "<p>…</p>" / `…` without ${}). Allow-listing the safe form catches
# variants like `el.innerHTML = items.map(b => `<li>${b.title}</li>`).join('')`
# that a deny-list missed in run #7.
# (whitespace sits inside the lookahead so backtracking can't skip the static-literal check)
_HTML_SINK = re.compile(r"\.(?:inner|outer)HTML\s*\+?=(?!=)(?!\s*(?:'[^'\n]*'|\"[^\"\n]*\"|`[^`$]*`)[ \t]*(?:;|$|\)|,))",
                        re.MULTILINE)
_INSERT_ADJ = re.compile(r"\.insertAdjacentHTML\s*\(")

RULES: list[tuple[str, tuple[str, ...], re.Pattern[str], str]] = [
    ("xss-innerhtml", (".js", ".html"), _HTML_SINK,
     "Gán innerHTML/outerHTML từ dữ liệu động → XSS. Dùng textContent hoặc createElement."),
    ("xss-insert-adjacent", (".js", ".html"), _INSERT_ADJ,
     "insertAdjacentHTML với dữ liệu động → XSS. Dùng createElement/textContent."),
    ("xss-document-write", (".js", ".html"), re.compile(r"document\.write(?:ln)?\s*\("),
     "document.write → XSS và chặn render."),
    ("js-eval", (".js", ".html"), re.compile(r"(?<![\w.])(?:eval|new\s+Function)\s*\("),
     "eval/new Function thực thi chuỗi tùy ý."),
    ("py-eval", (".py",), re.compile(r"(?<![\w.])(?:eval|exec)\s*\("), "eval/exec thực thi chuỗi tùy ý."),
    ("py-shell", (".py",), re.compile(r"\b(?:os\.system|os\.popen|subprocess\.)"),
     "Gọi lệnh hệ thống từ ứng dụng — không cần cho dự án này."),
    ("py-pickle", (".py",), re.compile(r"\bpickle\.loads?\s*\("), "pickle.load(s) trên dữ liệu không tin cậy."),
]

SCANNED_AREAS = ("backend", "frontend")


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    snippet: str
    message: str

    def describe(self) -> str:
        return f"[{self.rule}] {self.path}:{self.line} — {self.message}\n    {self.snippet}"

    def to_dict(self) -> dict:
        return asdict(self)


def scan_workspace(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for area in SCANNED_AREAS:
        base = root / area
        if not base.is_dir():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink()):
            rules = [r for r in RULES if path.suffix.lower() in r[1]]
            if not rules:
                continue
            text = path.read_text("utf-8", errors="replace")
            rel = path.relative_to(root).as_posix()
            for rule_id, _, pattern, message in rules:
                for match in pattern.finditer(text):
                    line_no = text.count("\n", 0, match.start()) + 1
                    snippet = text.splitlines()[line_no - 1].strip()[:200] if text else ""
                    findings.append(Finding(rule_id, rel, line_no, snippet, message))
    return findings
