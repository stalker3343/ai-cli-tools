#!/usr/bin/env python3
"""
run_vue_search.py — end-to-end Vue vacancy search, zero LLM context pollution.
Reads channels from config/.env, fetches posts, filters by Vue/Nuxt keywords,
writes a markdown file. Only the result path goes to stdout.

Usage:
  python scripts/run_vue_search.py [--period 14] [--channels chan1,chan2,...]

Output (stdout): path to cache/vacancies_vue_YYYY-MM-DD.md
Progress (stderr): channel count, post count, vacancy count
"""
import argparse, json, os, platform, re, subprocess, sys, datetime, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SKILLS_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILLS_DIR / "scripts"
CACHE_DIR = SKILLS_DIR / "cache"
CONFIG_FILE = SKILLS_DIR / "config" / ".env"

# ── spam / exclude filters ─────────────────────────────────────────────────
SPAM_PATTERNS = [
    '90% людей теряют',
    'папку с полезными каналами',
    'подработки в нашем боте',
    'Подработка на Авито',
    'карточкам товаров',
    'Личный ассистент SMM',
]
EXCLUDE_PATTERNS = [
    'Лучшие резюме',
    'Резюме за ',
    'Вакансии за ',
    'Обзор за ',
    ' Резюме ',
    '\U0001f4c3 Резюме',
    'пятница',
    'каналы в Max',
]

VUE_RE = re.compile(
    r'\bVue(?:\.js?|js|\d+)?\b|\bNuxt(?:\.js?|js|\d+)?\b|\bVuex\b|\bPinia\b',
    re.IGNORECASE,
)


def is_vacancy(text: str) -> bool:
    if not text.strip():
        return False
    for p in SPAM_PATTERNS + EXCLUDE_PATTERNS:
        if p in text:
            return False
    return True


def has_vue(text: str) -> bool:
    return bool(VUE_RE.search(text))


# ── helpers ────────────────────────────────────────────────────────────────
def read_channels_from_env() -> list[str]:
    if not CONFIG_FILE.exists():
        return []
    channels: list[str] = []
    with open(CONFIG_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TG_CHANNELS_WORK='):
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                channels.extend(c.strip() for c in val.split(',') if c.strip())
    return channels


def strip_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)  # space not empty — keeps word boundaries (e.g. Vue</b>АО → Vue АО)
    for ent, ch in [
        ('&#036;', '$'), ('&#8239;', ' '), ('&gt;', '>'),
        ('&lt;', '<'), ('&amp;', '&'), ('&nbsp;', ' '),
    ]:
        text = text.replace(ent, ch)
    return re.sub(r'\s+', ' ', text).strip()


def find_bash() -> str:
    if platform.system() == "Windows":
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        if os.path.exists(git_bash):
            return git_bash
        git_bash = r"C:\Program Files\Git\usr\bin\bash.exe"
        if os.path.exists(git_bash):
            return git_bash
    return "bash"


def posix_to_windows(path_str: str) -> Path:
    """Convert Git Bash POSIX path like /c/Users/... to C:\\Users\\..."""
    import re as _re
    m = _re.match(r'^/([a-zA-Z])(/.*)', path_str)
    if m:
        return Path(m.group(1).upper() + ':' + m.group(2).replace('/', '\\'))
    return Path(path_str)


def run_digest(channels_str: str, period: int) -> Path:
    script = SCRIPTS_DIR / "digest_json.sh"
    result = subprocess.run(
        [find_bash(), str(script), "--channels", channels_str, "--period", str(period)],
        capture_output=True, text=True, cwd=str(SKILLS_DIR),
    )
    if result.returncode != 0:
        print(f"digest_json.sh failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    raw_path = lines[-1]
    p = posix_to_windows(raw_path) if raw_path.startswith('/') else Path(raw_path)
    return p


def compact(json_path: Path) -> dict:
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    posts = [
        {
            'id': p['id'],
            'channel': p['channel'],
            'date': p['date'],
            'views': p.get('views', ''),
            'reactions': p.get('reactions', ''),
            'text': strip_html(p.get('text', ''))[:600],
        }
        for p in data['posts']
    ]
    return {'posts': posts, 'channels': data.get('channels', {})}


def filter_date_range(data: dict, from_date: str = '', to_date: str = '') -> dict:
    if not from_date and not to_date:
        return data

    filtered = []
    for p in data['posts']:
        post_date = p.get('date', '')[:10]
        if from_date and post_date < from_date:
            continue
        if to_date and post_date > to_date:
            continue
        filtered.append(p)
    return {**data, 'posts': filtered}


def filter_and_write(data: dict, output_path: Path, date_label: str = '') -> int:
    seen: set = set()
    results = []
    for p in sorted(data['posts'], key=lambda x: x['date'], reverse=True):
        key = (p['channel'], p['id'])
        if key in seen:
            continue
        seen.add(key)
        text = p.get('text', '')
        if is_vacancy(text) and has_vue(text):
            results.append(p)

    today = datetime.date.today().strftime('%Y-%m-%d')
    title_date = date_label or today
    lines = [
        f'# Vue-вакансии за {title_date}',
        '',
        f'Найдено: **{len(results)}** Vue/Nuxt вакансий',
        '',
    ]
    if date_label:
        lines.insert(1, f'Period: {date_label}')
        lines.insert(2, '')
    if not results:
        lines.append('_Вакансий с упоминанием Vue/Nuxt не найдено._')
    else:
        for v in results:
            url = f'https://t.me/{v["channel"]}/{v["id"]}'
            dt = v['date'][11:16] if len(v['date']) > 10 else v['date']
            lines += [
                '---',
                f'**[@{v["channel"]}]({url})** · {dt} · views: {v.get("views", "")}',
                v['text'][:600],
                '',
            ]

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    return len(results)


def main():
    parser = argparse.ArgumentParser(description='Find Vue vacancies in Telegram channels')
    parser.add_argument('--period', type=int, default=None, help='Days to look back (default: 14, or computed from --from-date)')
    parser.add_argument('--channels', default='', help='Comma-separated channels (default: from config/.env)')
    parser.add_argument('--from-date', default='', help='Inclusive start date, YYYY-MM-DD')
    parser.add_argument('--to-date', default='', help='Inclusive end date, YYYY-MM-DD')
    args = parser.parse_args()

    if args.channels:
        channels = [c.strip() for c in args.channels.split(',') if c.strip()]
    else:
        channels = read_channels_from_env()

    if not channels:
        print("ERROR: no channels. Pass --channels or configure config/.env", file=sys.stderr)
        sys.exit(1)

    if args.from_date:
        try:
            start_date = datetime.date.fromisoformat(args.from_date)
        except ValueError:
            print("ERROR: --from-date must be YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        start_date = None

    if args.to_date:
        try:
            datetime.date.fromisoformat(args.to_date)
        except ValueError:
            print("ERROR: --to-date must be YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    if args.from_date and args.to_date and args.from_date > args.to_date:
        print("ERROR: --from-date must be before or equal to --to-date", file=sys.stderr)
        sys.exit(1)

    period = args.period
    if period is None:
        period = 14
        if start_date:
            period = max((datetime.date.today() - start_date).days, 0)

    channels_str = ','.join(channels)
    print(f"Channels: {len(channels)}, period: {period} days", file=sys.stderr)

    json_path = run_digest(channels_str, period)
    data = compact(json_path)
    data = filter_date_range(data, args.from_date, args.to_date)
    print(f"Posts fetched: {len(data['posts'])}", file=sys.stderr)

    today = datetime.date.today().strftime('%Y-%m-%d')
    range_suffix = ''
    date_label = ''
    if args.from_date or args.to_date:
        from_label = args.from_date or 'beginning'
        to_label = args.to_date or 'today'
        range_suffix = f'_{from_label}_to_{to_label}'
        date_label = f'{from_label} - {to_label}'
    output_path = CACHE_DIR / f'vacancies_vue_{today}{range_suffix}.md'
    count = filter_and_write(data, output_path, date_label)
    print(f"Vue vacancies found: {count}", file=sys.stderr)

    print(str(output_path))


if __name__ == '__main__':
    main()
