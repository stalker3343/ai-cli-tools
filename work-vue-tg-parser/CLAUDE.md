# Личный набор скиллов

Эта папка — личная коллекция скиллов для Claude Code. Скиллы живут в `.claude/skills/`.

## Доступные скиллы

### telegram-channel-parser
Парсинг публичных Telegram-каналов через t.me/s/. Без токенов, без API-ключей.

**Быстрый старт:**
- "спарси канал @channel" → посты за последние N дней
- "дайджест AI каналов за сегодня" → дайджест из `.env` категории `ai`
- "топ постов @channel" → ранжирование по реакциям
- "сравни каналы channel1, channel2" → сравнительная таблица

**Скрипты** находятся в `.claude/skills/telegram-channel-parser/scripts/`.  
**Конфиг** (список каналов по категориям): `.claude/skills/telegram-channel-parser/config/.env`.

При запросе дайджеста — читай инструкции из `.claude/skills/telegram-channel-parser/SKILL.md`.

## Как добавить новый скилл

```
.claude/skills/<skill-name>/
├── SKILL.md       # инструкции для агента
├── scripts/       # исполняемые скрипты
├── config/        # конфиги и .env
└── assets/        # шаблоны
```
