#!/usr/bin/env python3
"""
Filter Vue-related vacancy posts from digest JSON.
Removes: resumes, reviews, spam, empty posts, non-Vue vacancies.
Output: markdown file in cache/vacancies_vue_YYYY-MM-DD.md
Usage: python scripts/filter_vacancies.py [path/to/digest_compact.json]
"""
import json, sys, io, datetime, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

# Vue.js и смежные технологии — все варианты написания
VUE_KEYWORDS = [
    r'\bVue\b', r'\bVue\.js\b', r'\bVueJS\b', r'\bVuejs\b',
    r'\bNuxt\b', r'\bNuxt\.js\b', r'\bNuxtJS\b',
    r'\bVuex\b', r'\bPinia\b',
    r'\bvue\b', r'\bnuxt\b',
]

VUE_RE = re.compile('|'.join(VUE_KEYWORDS), re.IGNORECASE)


def is_vacancy(post):
    text = post.get('text', '').strip()
    if not text:
        return False
    for pat in SPAM_PATTERNS:
        if pat in text:
            return False
    for pat in EXCLUDE_PATTERNS:
        if pat in text:
            return False
    return True


def has_vue(post):
    text = post.get('text', '')
    return bool(VUE_RE.search(text))


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else 'cache/digest_today_compact.json'
    if not os.path.exists(json_path):
        print(f'ERROR: file not found: {json_path}', file=sys.stderr)
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    seen = set()
    vue_vacancies = []
    for p in sorted(data['posts'], key=lambda x: x['date'], reverse=True):
        key = (p['channel'], p['id'])
        if key in seen:
            continue
        seen.add(key)
        if is_vacancy(p) and has_vue(p):
            vue_vacancies.append(p)

    today = datetime.date.today().strftime('%Y-%m-%d')
    lines = [
        f'# Vue-вакансии за {today}',
        '',
        f'Найдено: **{len(vue_vacancies)}** Vue/Nuxt вакансий',
        '',
    ]

    if not vue_vacancies:
        lines.append('_Вакансий с упоминанием Vue/Nuxt за сегодня не найдено._')
    else:
        for v in vue_vacancies:
            url = f'https://t.me/{v["channel"]}/{v["id"]}'
            views = v.get('views', '')
            dt = v['date'][11:16]
            lines.append('---')
            lines.append(f'**[@{v["channel"]}]({url})** · {dt} · views: {views}')
            lines.append(v['text'][:600])
            lines.append('')

    md = '\n'.join(lines)
    out = f'cache/vacancies_vue_{today}.md'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(md)

    print(out)
    print(f'Vue vacancies: {len(vue_vacancies)}', file=sys.stderr)


if __name__ == '__main__':
    main()
