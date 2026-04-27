# Монитор записи к врачу — er.center-zdorovie.ru

Скрипт проверяет расписание врача каждые 30 минут и уведомляет, когда появляется свободный слот.

---

## Быстрый запуск

```bash
# Установить зависимости (один раз)
pip install requests

# Запустить из папки со скриптом
python felitsin_checker.py
```

Лог пишется в `felitsin_log.txt` рядом со скриптом.  
Остановить: `Ctrl+C`.

**Авторизация не нужна** — API публичное, работает без куки.

---

## Как настроить для другого врача

Открыть скрипт и изменить параметры в блоке `# Настройки`:

```python
DOCTOR_ID   = "990005142"   # ID врача
FILIAL_ID   = "4"           # ID филиала
SPECLIST    = "1031"        # ID специальности
WEEKS_AHEAD = 8             # сколько недель вперёд смотреть
CHECK_EVERY = 1800          # интервал проверки в секундах (1800 = 30 мин)
```

### Как найти нужные ID

1. Открыть Chrome → F12 → Network → вкладка **Fetch/XHR**.
2. На сайте открыть расписание нужного врача.
3. Найти запрос вида:
   ```
   GET /api/reservation/schedule?st=...&en=...&doctor=XXX&filialId=YYY&speclist=ZZZ
   ```
4. Из URL скопировать:
   - `doctor=` → `DOCTOR_ID`
   - `filialId=` → `FILIAL_ID`
   - `speclist=` → `SPECLIST`

---

## Как устроен API

### Эндпоинт расписания

```
GET https://er.center-zdorovie.ru/api/reservation/schedule
```

**Параметры:**

| Параметр    | Пример       | Описание                              |
|-------------|--------------|---------------------------------------|
| `st`        | `20260427`   | Начало недели (формат YYYYMMDD)       |
| `en`        | `20260503`   | Конец недели (YYYYMMDD)               |
| `doctor`    | `990005142`  | ID врача                              |
| `filialId`  | `4`          | ID филиала                            |
| `speclist`  | `1031`       | ID специальности                      |
| `onlineMode`| `0`          | 0 = офлайн-запись, 1 = онлайн         |
| `_`         | `1776942758` | Timestamp-кешбастер (можно любой)     |

Сайт загружает расписание понедельно: одна неделя = один запрос.

### Формат ответа

```json
{
  "success": true,
  "data": [
    {
      "dname": "Фелицин Игорь Сергеевич",
      "freeCount": 0,
      "intervals": [
        {
          "workDate": "20260427",
          "startInterval": "10:00",
          "endInterval":   "13:40",
          "isFree":      false,
          "isAvailable": false,
          "filialName":  "АПО №5 по адресу пер.Днепровский,д.122/1",
          "schedident":  40199331
        }
      ]
    }
  ]
}
```

**Свободный слот:** `isFree: true` + `isAvailable: true`.  
**`freeCount`** — количество свободных слотов на неделю (быстрая проверка без перебора).  
Если `data: []` — врач в эту неделю не работает.

---

## Обязательные заголовки запроса

```
x-requested-with: XMLHttpRequest
x-integration-type: PORTAL
referer: https://er.center-zdorovie.ru/specialists
```

---

## Уведомления

- **Windows Toast** — всплывающее уведомление в трее (через PowerShell).
- **Звук** — длинный повторяющийся сигнал через `winsound`.
- **Лог** — все события пишутся в `felitsin_log.txt`.
