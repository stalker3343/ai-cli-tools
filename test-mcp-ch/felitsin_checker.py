"""
Монитор свободных слотов к Фелицину Игорю Сергеевичу
er.center-zdorovie.ru

Запуск: python felitsin_checker.py
Зависимости: pip install requests

Как работает авторизация:
  Сервер (Play Framework) продлевает сессию с каждым ответом через set-cookie.
  Скрипт автоматически подхватывает обновлённые куки — сессия живёт бесконечно,
  пока скрипт работает. При первом запуске куки нужно вставить вручную один раз.
  Если скрипт был остановлен дольше таймаута сессии — куки нужно обновить снова.
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
CHECK_EVERY  = 1800          # секунд между полными проверками расписания (30 мин)
                             # — достаточно часто чтобы сессия не протухла
LOG_FILE     = "felitsin_log.txt"
SITE         = "er.center-zdorovie.ru"

# ── Куки — вставить один раз при первом запуске ────────────────────────────
# Как получить: F12 в Chrome → Network → любой запрос к er.center-zdorovie.ru
#               → Request Headers → Cookie → скопировать три значения ниже.
# После этого скрипт сам будет их обновлять из set-cookie ответов.
COOKIES: dict[str, str] = {
    "PLAY_SESSION": "889fa5d265f7e0c1a1c1ff4d6102fc41d343726c-host.id=5613b41bdcd41ba17de0e72f",
    "WR_SESSION": (
        "7226ba9c5e1385f70dbf4521db999a018580a47e2-ZIg4MpqsomcPRJPGI+ZBRmQhJQLQ0f7b5J9lIx4vqM3Kf"
        "CmttoW6phkbfwMkkUu0k1lUqc8GvQ5GTItZYu4ZZnJkzbu6vy2O8IHH2c27Ro9Qwk0uqaHA46XM/d7rnIkgvSP"
        "zWPQWougjzS2MxO7bsBqyRXxT//hV4B3wb/sJFb0nBEhjliUSi87JG15pKtKq8UPL+RemEuvm48Y7iZyIkmS49E"
        "PlpRxrXBOgebKFP1uGOagoZUSKmqWzT4ic5Ji4j8AW2vqJW1OFchRFDry8SRoZkgoe785lmq4j4gcwTTBjAeklV"
        "pnrz3chbg=="
    ),
    "WR_DETAIL": (
        "2-pM8/3NLOM6nWsgg3WGwleha4303HrG4z1q0Eijj/S9tDt6gwbJXAz8uTGN8PKcdwmZBPxPBVs30/Z77jiwvP"
        "ZP/4bXHnEkhDrnO54NKYPrpV8+06glb35HR3H3RM3sDqXIwIkXVUnseOmJMcJ02ABzzyWfbS43gPEjLuxMW/oAn"
        "nQ1EK+/m/YL9sBrWwm0jHta7U4MGJuMONBVuQ2ATTmaO3KhW9YgbrYsCrV/4YmTjw8oVnypYXm3by54vtCi4Zp"
        "mUtYdvKIA7zUL5Y+1VuAe+xRB1Zpw7GxNuLInrwMkzYxrsnz7JeIthCwpaGtup4Z8vgj/GtuyxGyA0rSUtWZiA"
        "cKs71hmYLN0JqHDvS6IlevR6WiJiJYh/6+9lzrOfV1bxt4XL5uYb/e5tkG3et6tNMooJ/MmjJ6o+4y4SI8PhjS"
        "s2n1kBnkT56WD/EAUFARs6lkPLBVDPue/SWl1bMZulGtFsbgmjNGK6v0z1ZZ84HhyVWDz2FKjrSAR9sH12TeXw"
        "mry1CZWlxco6q2PwJQOQ03iTyX47qjhgEI9V+umCfCDbbQb0Wc6OTDWVMI3jCLlCzp6sGuWzfoa6TNEE7IaNUb"
        "Kh70yG5RzKvZQ3zXNr6B8SGBbTroNWf2kmgX8InoIlwDbAH/2Ye+CTNRKjYDWOCYPzheJ/Uk6ULl4DaIxraSRg"
        "A1xYKRb6ezNQfEv0+zJ6Boc730dyscxZNDxtd3v/fd02e+VSGaGykARSfb2zr8t9ayCo06EPH4EA+zDSoXTn6CZ"
        "whcR3Omt3nt7UTnZvjU4U="
    ),
    "_ym_uid": "1758016976542506873",
    "_ym_d": "1765538382",
    "_ym_isad": "2",
    "hideModal": "true",
    "WR_FLASH": "",
}

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

BASE_URL    = f"https://{SITE}/api/reservation/schedule"
SESSION_URL = f"https://{SITE}/logged-in"


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
        for _ in range(5):
            winsound.Beep(1000, 400)
            time.sleep(0.2)
    except Exception:
        pass


def update_cookies(resp: requests.Response) -> None:
    """Подхватывает обновлённые куки из set-cookie — именно так сессия продлевается."""
    for name, val in resp.cookies.items():
        COOKIES[name] = val


# ── API ───────────────────────────────────────────────────────────────────────

class SessionExpiredError(Exception):
    pass


def ping_session() -> bool:
    """
    Лёгкий запрос к /logged-in. Обновляет куки и возвращает True если сессия жива.
    Вызывается перед каждым циклом проверки.
    """
    try:
        r = requests.get(
            SESSION_URL,
            headers=HEADERS,
            cookies=COOKIES,
            params={"_": int(time.time() * 1000)},
            timeout=15,
            allow_redirects=False,
        )
        update_cookies(r)
        return r.json().get("authenticated", False)
    except Exception:
        return False


def week_range(start: datetime) -> tuple[str, str]:
    return start.strftime("%Y%m%d"), (start + timedelta(days=6)).strftime("%Y%m%d")


def check_week(st: str, en: str) -> list[dict]:
    r = requests.get(
        BASE_URL,
        headers=HEADERS,
        cookies=COOKIES,
        params={
            "st": st, "en": en,
            "doctor": DOCTOR_ID, "filialId": FILIAL_ID,
            "speclist": SPECLIST, "onlineMode": "0",
            "_": str(int(time.time() * 1000)),
        },
        timeout=20,
        allow_redirects=False,
    )

    if r.status_code in (301, 302, 303):
        raise SessionExpiredError("редирект на логин")

    update_cookies(r)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    body = r.json()
    if not body.get("success"):
        errors = body.get("errors", [])
        if any(e.get("status") in (401, 403) for e in errors):
            raise SessionExpiredError("ошибка авторизации в API")
        return []

    free = []
    for doc in body.get("data", []):
        for iv in doc.get("intervals", []):
            if iv.get("isFree") and iv.get("isAvailable"):
                free.append({
                    "date":      iv["workDate"],
                    "start":     iv["startInterval"],
                    "end":       iv["endInterval"],
                    "filial":    iv.get("filialName", ""),
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

        # Пингуем сессию — это автоматически продлевает куки через set-cookie
        alive = ping_session()
        if not alive:
            log(
                "СЕССИЯ ИСТЕКЛА. Скрипт был остановлен слишком долго. "
                "Зайдите на сайт в Chrome, скопируйте куки в COOKIES и перезапустите."
            )
            log(f"Повторная попытка через {CHECK_EVERY // 60} мин.")
            time.sleep(CHECK_EVERY)
            continue

        found_any_new = False

        for week_idx in range(WEEKS_AHEAD):
            week_start = monday + timedelta(weeks=week_idx)
            st, en = week_range(week_start)
            slots = None
            for attempt in range(2):
                try:
                    slots = check_week(st, en)
                    time.sleep(1)
                    break
                except SessionExpiredError as e:
                    log(f"  Сессия умерла в процессе ({e}). Прерываю цикл.")
                    slots = None
                    break
                except Exception as e:
                    if attempt == 0:
                        time.sleep(5)  # короткая пауза перед повтором
                    else:
                        log(f"  Ошибка {st}-{en}: {e}")
            if slots is None:
                continue

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

        if not found_any_new:
            log(f"Свободных слотов нет. Следующая проверка через {CHECK_EVERY // 60} мин.")

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
