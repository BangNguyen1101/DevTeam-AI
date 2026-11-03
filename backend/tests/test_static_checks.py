from app.ai_core.execution.static_checks import scan_workspace


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rules(root):
    return sorted((f.rule, f.path, f.line) for f in scan_workspace(root))


def test_flags_dynamic_html_sinks(tmp_path):
    # The exact pattern Gemini produced in runs #5 and #6
    write(tmp_path, "frontend/app.js",
          "list.innerHTML = '';\n"
          "li.innerHTML = `<b>${book.title}</b>`;\n"
          "row.innerHTML = '<td>' + book.author + '</td>';\n"
          "el.insertAdjacentHTML('beforeend', html);\n"
          "document.write(x);\n")
    assert rules(tmp_path) == [
        ("xss-document-write", "frontend/app.js", 5),
        ("xss-innerhtml", "frontend/app.js", 2),
        ("xss-innerhtml", "frontend/app.js", 3),
        ("xss-insert-adjacent", "frontend/app.js", 4),
    ]


def test_flags_any_dynamic_right_hand_side(tmp_path):
    # Missed by the first version of the scanner in run #7
    write(tmp_path, "frontend/app.js",
          "list.innerHTML = books.map(b => `\n  <li>${b.title}</li>\n`).join('');\n"
          "card.innerHTML = html;\n"
          "x.innerHTML += render(item)\n")
    assert rules(tmp_path) == [
        ("xss-innerhtml", "frontend/app.js", 1),
        ("xss-innerhtml", "frontend/app.js", 4),
        ("xss-innerhtml", "frontend/app.js", 5),
    ]


def test_safe_dom_code_is_not_flagged(tmp_path):
    write(tmp_path, "frontend/app.js",
          "list.innerHTML = '';\n"
          "list.innerHTML = \"\"\n"
          "box.innerHTML = `<p>Đang tải…</p>`;\n"
          "if (el.innerHTML === '') {}\n"
          "td.textContent = book.title;\n"
          "const evaluate = 1; obj.eval = 2;\n")
    assert rules(tmp_path) == []


def test_flags_dangerous_python(tmp_path):
    write(tmp_path, "backend/app/main.py",
          "import os, pickle, subprocess\n"
          "eval(x)\n"
          "os.system('ls')\n"
          "subprocess.run(['ls'])\n"
          "pickle.loads(b)\n"
          "def evaluate(): pass\n")
    assert [r[0] for r in rules(tmp_path)] == ["py-eval", "py-pickle", "py-shell", "py-shell"]


def test_only_backend_and_frontend_are_scanned(tmp_path):
    write(tmp_path, "tests/test_x.py", "eval('1')\n")
    write(tmp_path, "docs/SRS.md", "el.innerHTML = `${x}`\n")
    assert rules(tmp_path) == []
