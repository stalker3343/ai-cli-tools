const fs = require("fs");

/**
 * Функция для чтения JSON файла и записи сообщений в текстовый файл
 * @param {string} inputFile - Путь к входному JSON файлу
 * @param {string} outputFile - Путь к выходному текстовому файлу
 * @returns {Promise<void>}
 */
async function processMessages(inputFile, outputFile) {
  try {
    // Читаем JSON файл
    const jsonData = fs.readFileSync(inputFile, "utf8");
    const messages = JSON.parse(jsonData);

    // Извлекаем сообщения и объединяем их с переносом строки
    const messageText = messages.map((item) => item.message).join("\n");

    // Записываем результат в текстовый файл
    fs.writeFileSync(outputFile, messageText, "utf8");

    console.log(
      `Успешно записано ${messages.length} сообщений в файл ${outputFile}`
    );
  } catch (error) {
    console.error("Произошла ошибка:", error.message);
  }
}

// Запускаем обработку
processMessages("mess.json", "messages.txt");
