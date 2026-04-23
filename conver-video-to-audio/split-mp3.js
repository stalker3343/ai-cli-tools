const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// Получаем аргументы командной строки
const args = process.argv.slice(2);

// Длина сегмента в секундах (9 минут = 540 секунд)
const SEGMENT_DURATION = 540;

// Проверка наличия FFmpeg в системе
function checkFFmpeg() {
  return new Promise((resolve, reject) => {
    exec('ffmpeg -version', (error) => {
      if (error) {
        reject(new Error('FFmpeg не найден в PATH. Убедитесь, что FFmpeg установлен и доступен через команду "ffmpeg" в консоли.'));
      } else {
        resolve();
      }
    });
  });
}

// Получение длительности аудио файла
function getAudioDuration(filePath) {
  return new Promise((resolve, reject) => {
    exec(`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`, (error, stdout) => {
      if (error) {
        reject(new Error(`Не удалось получить длительность файла: ${error.message}`));
      } else {
        const duration = parseFloat(stdout.trim());
        resolve(isNaN(duration) ? 0 : duration);
      }
    });
  });
}

// Разрезание одного MP3 файла на сегменты
async function splitMp3File(inputPath) {
  return new Promise(async (resolve, reject) => {
    // Проверяем существование файла
    if (!fs.existsSync(inputPath)) {
      reject(new Error(`Файл не найден: ${inputPath}`));
      return;
    }

    // Проверяем расширение
    if (path.extname(inputPath).toLowerCase() !== '.mp3') {
      reject(new Error(`Файл не является MP3: ${inputPath}`));
      return;
    }

    try {
      // Получаем длительность файла
      const duration = await getAudioDuration(inputPath);
      console.log(`\nФайл: ${path.basename(inputPath)}`);
      console.log(`Длительность: ${Math.floor(duration / 60)} мин ${Math.floor(duration % 60)} сек`);

      // Создаем папку для сегментов
      const fileNameWithoutExt = path.basename(inputPath, path.extname(inputPath));
      const outputDir = path.join(path.dirname(inputPath), fileNameWithoutExt);

      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
        console.log(`Создана папка: ${outputDir}`);
      }

      // Вычисляем количество сегментов
      const segmentCount = Math.ceil(duration / SEGMENT_DURATION);
      console.log(`Будет создано сегментов: ${segmentCount}\n`);

      // Разрезаем файл на сегменты
      const segments = [];
      for (let i = 0; i < segmentCount; i++) {
        const startTime = i * SEGMENT_DURATION;
        const segmentNumber = (i + 1).toString().padStart(3, '0');
        const outputFile = path.join(outputDir, `${fileNameWithoutExt}_part${segmentNumber}.mp3`);

        await new Promise((segmentResolve, segmentReject) => {
          // Для последнего сегмента не указываем длительность, чтобы взять всё оставшееся
          const command = i === segmentCount - 1
            ? `ffmpeg -i "${inputPath}" -ss ${startTime} -c copy "${outputFile}" -y`
            : `ffmpeg -i "${inputPath}" -ss ${startTime} -t ${SEGMENT_DURATION} -c copy "${outputFile}" -y`;

          console.log(`Создание сегмента ${i + 1}/${segmentCount}...`);

          exec(command, (error, stdout, stderr) => {
            if (error && !stderr.includes('Output')) {
              segmentReject(new Error(`Ошибка при создании сегмента ${i + 1}: ${error.message}`));
            } else {
              segments.push(outputFile);
              const segmentStart = Math.floor(startTime / 60);
              const segmentStartSec = Math.floor(startTime % 60);
              console.log(`✓ Сегмент ${i + 1} создан: ${path.basename(outputFile)} (с ${segmentStart}:${segmentStartSec.toString().padStart(2, '0')})`);
              segmentResolve();
            }
          });
        });
      }

      console.log(`\n✓ Все сегменты сохранены в папку: ${outputDir}`);
      resolve({ inputPath, outputDir, segments });
    } catch (error) {
      reject(error);
    }
  });
}

// Обработка файла или директории
async function processInput(inputPath) {
  const fullPath = path.resolve(inputPath);
  const stat = fs.statSync(fullPath);

  if (stat.isFile()) {
    // Обработка одного файла
    await splitMp3File(fullPath);
  } else if (stat.isDirectory()) {
    // Обработка всех MP3 файлов в директории
    const files = fs.readdirSync(fullPath);
    const mp3Files = files.filter(file =>
      path.extname(file).toLowerCase() === '.mp3'
    );

    if (mp3Files.length === 0) {
      console.log('MP3 файлы не найдены в директории');
      return;
    }

    console.log(`Найдено ${mp3Files.length} MP3 файл(ов) для разрезания\n`);

    for (const file of mp3Files) {
      const inputFile = path.join(fullPath, file);
      try {
        await splitMp3File(inputFile);
        console.log(''); // Пустая строка для разделения
      } catch (error) {
        console.error(`Ошибка при обработке ${file}:`, error.message);
      }
    }
  }
}

// Главная функция
async function main() {
  if (args.length === 0) {
    console.log('Использование: node split-mp3.js <путь_к_файлу_или_папке>');
    console.log('Примеры:');
    console.log('  node split-mp3.js audio.mp3');
    console.log('  node split-mp3.js ./audio-files');
    console.log('  node split-mp3.js "C:\\Users\\Artem\\Desktop\\audio.mp3"');
    console.log('\nСкрипт разрежет MP3 файлы на сегменты по 9 минут.');
    process.exit(1);
  }

  // Проверяем наличие FFmpeg
  try {
    await checkFFmpeg();
  } catch (error) {
    console.error('\n✗', error.message);
    process.exit(1);
  }

  const inputPath = args[0];

  try {
    await processInput(inputPath);
    console.log('\n✓ Все файлы обработаны!');
  } catch (error) {
    console.error('\n✗ Ошибка:', error.message);
    process.exit(1);
  }
}

// Запуск
main();
