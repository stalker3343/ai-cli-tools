const config = {
  // Get these values at https://my.telegram.org -> API development tools.
  api_id: 123456,
  api_hash: "your_api_hash",

  // Phone number of the Telegram account that has access to the chats.
  phone: "+79990000000",

  // Optional 2FA password. Leave empty if two-step verification is disabled.
  password: "",

  // Optional saved Telegram session string. Leave empty for the first login.
  session: "",
};

module.exports = config;
