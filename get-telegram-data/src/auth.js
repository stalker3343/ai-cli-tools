const { phone, password } = require("../config.js");
const api = require("./api");
const input = require("input");

async function getUser() {
  try {
    const user = await api.call("users.getFullUser", {
      id: {
        _: "inputUserSelf",
      },
    });
    return user;
  } catch (error) {
    return null;
  }
}

const auth = async () => {
  const client = api.getClient();
  await client.connect();

  const user = await getUser();

  if (!user) {
    try {
      // Подключаемся к Telegram
      await client.start({
        phoneNumber: async () => phone,
        password: async () =>
          password || (await input.text("Введите пароль 2FA (если есть): ")),
        phoneCode: async () =>
          await input.text("Введите код, который пришел в Telegram: "),
        onError: (err) => console.log(err),
      });

      console.log("Вы успешно вошли в систему!");

      // Сохраняем строку сессии для последующего использования
      console.log("Строка сессии:", client.session.save());
    } catch (error) {
      console.error("Ошибка авторизации:", error);
      throw error;
    }
  }
};

module.exports = auth;
