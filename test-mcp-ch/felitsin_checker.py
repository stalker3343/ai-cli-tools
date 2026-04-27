"""
Монитор свободных слотов к Фелицину Игорю Сергеевичу
er.center-zdorovie.ru

Запуск: python felitsin_checker.py
Зависимости: pip install requests
"""

import requests
import time
import sys
import io
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Настройки ──────────────────────────────────────────────────────────────
DOCTOR_ID    = "990005142"   # Фелицин Игорь Сергеевич
FILIAL_ID    = "4"
SPECLIST     = "1031"
WEEKS_AHEAD  = 8             # сколько недель вперёд проверять
CHECK_EVERY  = 900           # секунд между полными проверками (15 мин)
LOG_FILE     = "felitsin_log.txt"
SITE         = "er.center-zdorovie.ru"

HEADERS = {
    "accept": "*/*",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "referer": f"https://{SITE}/specialists",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
    "x-integration-type": "PORTAL",
    "x-requested-with": "XMLHttpRequest",
}

BASE_URL = f"https://{SITE}/api/reservation/schedule"


# ── Утилиты ──────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify_windows(title: str, body: str) -> None:
    body_safe  = body.replace("'", "`'")
    title_safe = title.replace("'", "`'")
    script = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"$n = New-Object System.Windows.Forms.NotifyIcon; "
        f"$n.Icon = [System.Drawing.SystemIcons]::Information; "
        f"$n.Visible = $true; "
        f"$n.ShowBalloonTip(10000, '{title_safe}', '{body_safe}', "
        f"[System.Windows.Forms.ToolTipIcon]::Info); "
        f"Start-Sleep -Seconds 12; $n.Dispose()"
    )
    try:
        import subprocess
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=0x08000000,
        )
    except Exception as e:
        log(f"  Не удалось отправить уведомление: {e}")


def beep() -> None:
    try:
        import winsound
        for _ in range(500):
            winsound.Beep(1000, 400)
            time.sleep(2)
    except Exception:
        pass


# ── API ───────────────────────────────────────────────────────────────────────

def week_range(start: datetime) -> tuple[str, str]:
    return start.strftime("%Y%m%d"), (start + timedelta(days=6)).strftime("%Y%m%d")


def check_week(st: str, en: str) -> list[dict]:
    r = requests.get(
        BASE_URL,
        headers=HEADERS,
        params={
            "st": st, "en": en,
            "doctor": DOCTOR_ID, "filialId": FILIAL_ID,
            "speclist": SPECLIST, "onlineMode": "0",
            "_": str(int(time.time() * 1000)),
        },
        timeout=20,
    )

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    body = r.json()
    if not body.get("success"):
        return []

    free = []
    for doc in body.get("data", []):
        for iv in doc.get("intervals", []):
            if iv.get("isFree") and iv.get("isAvailable"):
                free.append({
                    "date":       iv["workDate"],
                    "start":      iv["startInterval"],
                    "end":        iv["endInterval"],
                    "filial":     iv.get("filialName", ""),
                    "schedident": iv["schedident"],
                })
    return free


# ── Основной цикл ─────────────────────────────────────────────────────────────

def run() -> None:
    log("=" * 60)
    log("Монитор запущен. Врач: Фелицин Игорь Сергеевич")
    log(f"Интервал: {CHECK_EVERY // 60} мин., горизонт: {WEEKS_AHEAD} нед.")
    log("=" * 60)

    known_free: set[str] = set()

    while True:
        now    = datetime.now()
        monday = now - timedelta(days=now.weekday())

        found_any_new = False
        total_free = 0

        log("-" * 60)
        for week_idx in range(WEEKS_AHEAD):
            week_start = monday + timedelta(weeks=week_idx)
            st, en = week_range(week_start)
            slots = None
            for attempt in range(2):
                try:
                    slots = check_week(st, en)
                    time.sleep(1)
                    break
                except Exception as e:
                    if attempt == 0:
                        time.sleep(5)
                    else:
                        log(f"  Ошибка {st}-{en}: {e}")
            if slots is None:
                log(f"  Неделя {st}-{en}: ошибка запроса")
                continue

            week_label = f"{week_start.strftime('%d.%m')}–{(week_start + timedelta(days=6)).strftime('%d.%m')}"
            if slots:
                total_free += len(slots)
                slot_strs = ", ".join(f"{s['date'][6:8]}.{s['date'][4:6]} {s['start']}" for s in slots)
                log(f"  {week_label}: {len(slots)} своб. → {slot_strs}")
            else:
                log(f"  {week_label}: нет свободных")

            for slot in slots:
                key = f"{slot['date']}_{slot['start']}_{slot['schedident']}"
                if key not in known_free:
                    known_free.add(key)
                    msg = (
                        f"СВОБОДНЫЙ СЛОТ: {slot['date']} "
                        f"{slot['start']}-{slot['end']} | {slot['filial']}"
                    )
                    log(f"*** {msg} ***")
                    notify_windows("Фелицин — свободный слот!", msg)
                    beep()
                    found_any_new = True

        log(f"Итого свободных: {total_free}. Следующая проверка через {CHECK_EVERY // 60} мин.")
        log("-" * 60)

        # Чистим прошедшие даты из памяти
        cutoff    = now.strftime("%Y%m%d")
        known_free = {k for k in known_free if k[:8] >= cutoff}

        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log("Остановлено пользователем.")
        sys.exit(0)
