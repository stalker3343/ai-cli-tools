const { TelegramClient } = require("telegram");
const { StringSession } = require("telegram/sessions");
const { api_id, api_hash, session } = require("../config.js");

class API {
  constructor() {
    // Keep the real session in local config.js so this source file is safe to commit.
    this.stringSession = new StringSession(session || "");

    this.client = new TelegramClient(this.stringSession, api_id, api_hash, {
      connectionRetries: 5,
    });
  }

  async call(method, params, options = {}) {
    try {
      switch (method) {
        case "messages.getAllChats":
          const dialogs = await this.client.getDialogs();
          return {
            chats: dialogs.map((dialog) => ({
              id: dialog.id,
              title: dialog.title,
              _: "chat",
            })),
          };

        case "messages.getHistory":
          const messages = await this.client.getMessages(
            params.peer.channel_id,
            {
              limit: params.limit,
              offset: params.add_offset || 0,
            }
          );
          return { messages, count: messages.length };

        case "users.getFullUser":
          const user = await this.client.getMe();
          return user;

        default:
          throw new Error(`Method ${method} is not implemented`);
      }
    } catch (error) {
      console.log(`${method} error:`, error);
      throw error;
    }
  }

  getClient() {
    return this.client;
  }
}

const api = new API();
module.exports = api;
