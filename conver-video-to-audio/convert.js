const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// Получаем аргументы командной строки
const args = process.argv.slice(2);

// Проверка наличия FFmpeg в системе
function checkFFmpeg() {
  return new Promise((resolve, reject) => {
    exec('ffmpeg -version', (error) => {
      if (error) {
        reject(new Error('FFmpeg не найден в PATH. Убедитесь, что FFmpeg установлен и доступен через команду "ffmpeg" в консоли.\n' +
          'После установки перезапустите терминал.'));
      } else {
        resolve();
      }
    });
  });
}

// Функция для конвертации одного файла
function convertMp4ToMp3(inputPath, outputPath) {
  return new Promise((resolve, reject) => {
    // Проверяем существование входного файла
    if (!fs.existsSync(inputPath)) {
      reject(new Error(`Файл не найден: ${inputPath}`));
      return;
    }

    console.log(`Конвертация: ${path.basename(inputPath)} -> ${path.basename(outputPath)}`);

    // Экранируем пути для Windows
    const escapedInput = inputPath.replace(/"/g, '\\"');
    const escapedOutput = outputPath.replace(/"/g, '\\"');

    // Команда FFmpeg для конвертации MP4 в MP3
    const command = `ffmpeg -i "${escapedInput}" -vn -acodec libmp3lame -ab 192k -ar 44100 -ac 2 "${escapedOutput}" -y`;

    console.log('Выполняется команда: ffmpeg ...');

    const ffmpegProcess = exec(command, (error, stdout, stderr) => {
      if (error) {
        // FFmpeg пишет прогресс в stderr, это нормально
        if (error.code === 1 && stderr.includes('Output')) {
          // Успешное завершение
          console.log(`✓ Конвертация завершена: ${path.basename(outputPath)}`);
          resolve(outputPath);
        } else {
          console.error('Ошибка конвертации:', error.message);
          reject(error);
        }
      } else {
        console.log(`✓ Конвертация завершена: ${path.basename(outputPath)}`);
        resolve(outputPath);
      }
    });

    // Выводим прогресс из stderr (FFmpeg пишет прогресс туда)
    ffmpegProcess.stderr.on('data', (data) => {
      const output = data.toString();
      // Ищем строки с прогрессом (например: "time=00:01:23.45 bitrate= 192.0kbits/s")
      const timeMatch = output.match(/time=(\d+):(\d+):(\d+\.\d+)/);
      if (timeMatch) {
        const hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const seconds = parseFloat(timeMatch[3]);
        const totalSeconds = hours * 3600 + minutes * 60 + seconds;
        process.stdout.write(`\rОбработано: ${Math.floor(totalSeconds)} сек.`);
      }
    });
  });
}

// Функция для обработки файла или директории
async function processInput(inputPath) {
  const fullPath = path.resolve(inputPath);
  const stat = fs.statSync(fullPath);

  if (stat.isFile()) {
    // Обработка одного файла
    if (path.extname(fullPath).toLowerCase() !== '.mp4') {
      console.warn(`Предупреждение: ${fullPath} не является MP4 файлом`);
    }
    const outputPath = fullPath.replace(/\.mp4$/i, '.mp3');
    await convertMp4ToMp3(fullPath, outputPath);
  } else if (stat.isDirectory()) {
    // Обработка всех MP4 файлов в директории
    const files = fs.readdirSync(fullPath);
    const mp4Files = files.filter(file =>
      path.extname(file).toLowerCase() === '.mp4'
    );

    if (mp4Files.length === 0) {
      console.log('MP4 файлы не найдены в директории');
      return;
    }

    console.log(`Найдено ${mp4Files.length} MP4 файл(ов) для конвертации\n`);

    for (const file of mp4Files) {
      const inputFile = path.join(fullPath, file);
      const outputFile = inputFile.replace(/\.mp4$/i, '.mp3');
      try {
        await convertMp4ToMp3(inputFile, outputFile);
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
    console.log('Использование: node convert.js <путь_к_файлу_или_папке>');
    console.log('Примеры:');
    console.log('  node convert.js video.mp4');
    console.log('  node convert.js ./videos');
    console.log('  node convert.js "C:\\Users\\Artem\\Desktop\\video.mp4"');
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
    console.log('\n✓ Все конвертации завершены!');
  } catch (error) {
    console.error('\n✗ Ошибка:', error.message);
    process.exit(1);
  }
}

// Запуск
main();
