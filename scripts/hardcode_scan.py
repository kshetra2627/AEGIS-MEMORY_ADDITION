"""Hardcode scan for active source files."""
import os, re

ACTIVE_FILES = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in (
        'worktree-1790581041182', '.venv', '__pycache__', '.git', '.claude', 'database', 'logs', 'data'
    )]
    for f in files:
        if f.endswith('.py') and not f.startswith('_t'):
            ACTIVE_FILES.append(os.path.join(root, f))

PATTERNS = [
    (r'Demo Login',                               'Demo Login button present'),
    (r"session_state\.authenticated\s*=\s*True",  'fake auth bypass'),
    (r'nwfs-seed-',                               'seed script literal ID in runtime code'),
    (r'gsk_[A-Za-z0-9]{20,}',                    'Groq API key literal'),
    (r'hsk_[0-9a-f]{20,}',                       'Hindsight API key literal'),
    (r'AQ\.Ab8[A-Za-z0-9+/=]{10,}',              'Gemini API key literal'),
    (r"\bfake_(user|memory|auth|result)\b",       'fake_ runtime variable'),
]

WHITELIST = {'tests', 'scripts'}

findings = []
for path in sorted(ACTIVE_FILES):
    in_whitelist = any(w in path.replace('\\', '/') for w in WHITELIST)
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for lineno, line in enumerate(fh, 1):
                for pattern, label in PATTERNS:
                    if re.search(pattern, line):
                        if in_whitelist and 'Demo Login' in label:
                            continue  # test files may check for absence
                        findings.append((path, lineno, label, line.strip()[:100]))
    except Exception as e:
        print(f'SKIP {path}: {e}')

if findings:
    print(f'FINDINGS ({len(findings)}):')
    for path, lineno, label, line in findings:
        print(f'  [{label}]  {path}:{lineno}  =>  {line}')
else:
    print('CLEAN: No suspicious runtime hardcoding found in active source files.')
