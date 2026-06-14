
Достать звук
ffmpeg -i anya-mero.mp4 -vn -ac 1 -ar 24000  -c:a aac -b:a 64k -movflags +faststart lesson-transcribe.m4a


# split-video

Разбивает `.mp4` на части по 9 минут (без перекодирования).

## Запуск

```
node split.mjs "видео.mp4"
```

На выходе: `видео_part1.mp4`, `видео_part2.mp4`, ...

## Требования

- Node.js
- ffmpeg (установлен через `winget install Gyan.FFmpeg`)
