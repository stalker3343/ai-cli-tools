const api = require("./src/api");
const auth = require("./src/auth");
const fs = require("fs");

// Получение чатов
// (async () => {
//   try {
//     await auth();

//     const chatsResp = await api.call("messages.getAllChats", {
//       except_ids: 10,
//     });

//     const chat = chatsResp.chats.filter(
//       (c) => c.title === "ОМ: Многоработничество"
//     );

//     console.log(chat);
//   } catch (error) {
//     console.error("Ошибка при получении чатов:", error);
//   }
// })();

// Получение сообщений
(async () => {
  await auth();

  const inputPeer = {
    _: "inputPeerChannel",
    access_hash: "17906011120624565020",
    channel_id: "-1001785866524",
  };

  const LIMIT_COUNT = 10000;
  const allMessages = [];

  const firstHistoryResult = await api.call("messages.getHistory", {
    peer: inputPeer,
    limit: LIMIT_COUNT,
  });

  const historyCount = firstHistoryResult.count;

  console.log(historyCount);

  for (let offset = 0; offset < historyCount; offset += LIMIT_COUNT) {
    console.log("offset", offset);
    const history = await api.call("messages.getHistory", {
      peer: inputPeer,
      limit: LIMIT_COUNT,
      add_offset: offset,
    });

    allMessages.push(
      ...history.messages.map((m) => ({
        date: m.date,
        message: m.message,
      }))
    );
  }

  fs.writeFileSync("mess.json", JSON.stringify(allMessages), "utf-8");
})();
