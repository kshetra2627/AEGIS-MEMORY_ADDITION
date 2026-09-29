"""
Comprehensive hardcode scan for active runtime files only.
Excludes: tests/, scripts/, worktree-*, .venv, _t234.py, _t5.py, database/, logs/, data/

Exit 0 = clean. Exit 1 = suspicious findings (review each manually).
"""
import os
import re
import sys

SKIP_DIRS = {
    'worktree-1790581041182', '.venv', '__pycache__', '.git', '.claude',
    'database', 'logs', 'data', 'tests', 'scripts', 'assets',
}
SKIP_FILES = {'_t234.py', '_t5.py', 'hardcode_scan.py'}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

active = []
for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
    for f in files:
        if f.endswith('.py') and f not in SKIP_FILES:
            active.append(os.path.join(root, f))

# Each tuple: (regex_pattern, label)
PATTERNS = [
    (r'Demo\s+Login',                                           'Demo Login present'),
    (r'session_state\.authenticated\s*=\s*True',                'fake auth bypass'),
    (r'session_state\[.authenticated.\]\s*=\s*True',            'fake auth bypass (bracket)'),
    (r'gsk_[A-Za-z0-9]{20,}',                                  'Groq API key literal'),
    (r'hsk_[0-9a-f]{20,}',                                     'Hindsight API key literal'),
    (r'AQ\.Ab[A-Za-z0-9+/=]{10,}',                             'Gemini API key literal'),
    (r'sk-or-v1-[A-Za-z0-9]{20,}',                             'OpenRouter API key literal'),
    (r'nwfs-seed-',                                             'seed-script ID used in runtime'),
    (r'from\s+scripts[\.\s]+seed_memory\s+import',             'seed script imported by runtime'),
    (r'import\s+seed_memory\b',                                 'seed script imported by runtime'),
    (r'memory_context\s*=\s*\[(?!\])',                          'hardcoded memory_context list'),
    (r'"FinSecure"|\'FinSecure\'',                              'FinSecure hardcoded in runtime'),
    (r'"nwfs-seed-|\'nwfs-seed-',                               'nwfs-seed ID string literal'),
]

findings = []
for path in sorted(active):
    rel = os.path.relpath(path, ROOT)
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()
        for lineno, raw in enumerate(lines, 1):
            stripped = raw.strip()
            is_comment = stripped.startswith('#')
            for pat, label in PATTERNS:
                if re.search(pat, raw):
                    # Pure comment lines don't count as runtime hardcoding
                    # (except API key literals which should never appear even in comments)
                    api_key_labels = {'Groq API key literal', 'Hindsight API key literal',
                                      'Gemini API key literal', 'OpenRouter API key literal'}
                    if is_comment and label not in api_key_labels:
                        continue
                    findings.append((rel, lineno, label, stripped[:110]))
    except Exception as e:
        print(f'SKIP {rel}: {e}')

if findings:
    print(f'FINDINGS ({len(findings)}):')
    for rel, n, lbl, ln in findings:
        print(f'  [{lbl}]  {rel}:{n}  =>  {ln}')
    print()
    print('Review each finding above. Findings in docstrings/f-strings may be false positives.')
    sys.exit(1)
else:
    print('CLEAN: No runtime hardcoding found in active application files.')
    sys.exit(0)
