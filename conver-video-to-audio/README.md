# convert-video-to-audio

```
node convert.js "video.mp4"       # конвертировать MP4 → MP3
node split-mp3.js "audio.mp3"     # разрезать MP3 на части по 9 минут
```

## Требования

Нужен [FFmpeg](https://ffmpeg.org/) — установить через winget:

```
winget install Gyan.FFmpeg
```

После установки перезапустить терминал и проверить:

```
ffmpeg -version
```

## Конвертация MP4 в MP3

```
node convert.js <файл_или_папка>
```

**Примеры:**
```
node convert.js "2026-05-28 09-49-35.mp4"
node convert.js ./videos
node convert.js "C:\Users\Artem\Desktop\video.mp4"
```

- Создаёт `.mp3` рядом с `.mp4`, оригинал не удаляется
- Битрейт: 192 kbps, 44100 Hz, стерео
- Если передать папку — конвертирует все MP4 внутри

## Разрезание MP3 на части

```
node split-mp3.js <файл_или_папка>
```

**Примеры:**
```
node split-mp3.js "audio.mp3"
node split-mp3.js ./audio-files
```

- Режет на сегменты по 9 минут
- Создаёт папку с именем файла и сохраняет туда части: `audio_part001.mp3`, `audio_part002.mp3`, ...
- Если передать папку — обрабатывает все MP3 внутри
