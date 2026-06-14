const fs = require("fs");
const path = require("path");
const { Api } = require("telegram");
const auth = require("./src/auth");
const api = require("./src/api");

function getArg(name, fallback = null) {
  const prefix = `--${name}=`;
  const value = process.argv.find((arg) => arg.startsWith(prefix));
  return value ? value.slice(prefix.length) : fallback;
}

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function parseTelegramPrivateLink(value) {
  const match = String(value || "").match(
    /^https?:\/\/t\.me\/c\/(\d+)\/(\d+)(?:\/(\d+))?/i
  );

  if (!match) {
    return null;
  }

  return {
    chatId: match[1],
    topicOrMessageId: match[2],
    commentId: match[3],
  };
}

function telegramIdVariants(value) {
  const raw = String(value || "").trim();
  if (!/^-?\d+$/.test(raw)) {
    return [raw];
  }

  const unsigned = raw.replace(/^-100/, "").replace(/^-/, "");
  return Array.from(new Set([raw, unsigned, `-100${unsigned}`, `-${unsigned}`]));
}

function safeFileName(value) {
  return String(value || "chat")
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 120);
}

function pick(...values) {
  return values.find((value) => value !== undefined && value !== null);
}

function dialogMatches(dialog, query) {
  const normalizedQuery = normalize(query).replace(/^@/, "");
  const entity = dialog.entity || {};
  const link = parseTelegramPrivateLink(query);
  const queryVariants = link
    ? telegramIdVariants(link.chatId).map(normalize)
    : telegramIdVariants(normalizedQuery).map(normalize);
  const values = [
    dialog.title,
    entity.title,
    entity.username,
    dialog.id && String(dialog.id),
    entity.id && String(entity.id),
  ]
    .flatMap((value) => telegramIdVariants(value))
    .map(normalize);

  return values.some((value) => {
    const normalizedValue = value.replace(/^@/, "");
    return queryVariants.some(
      (queryVariant) =>
        normalizedValue === queryVariant ||
        normalizedValue.includes(queryVariant.replace(/^@/, ""))
    );
  });
}

function topicTitle(topic) {
  return pick(topic.title, topic.name, "");
}

function topicId(topic) {
  return pick(topic.id, topic.topicId, topic.topic_id);
}

function topicMessageId(topic) {
  return pick(topic.topMessage, topic.top_message, topicId(topic));
}

function topicMatches(topic, query) {
  const normalizedQuery = normalize(query);
  const title = normalize(topicTitle(topic));
  const id = topicId(topic);

  return (
    title === normalizedQuery ||
    title.includes(normalizedQuery) ||
    String(id) === String(query)
  );
}

function isIntegerString(value) {
  return /^\d+$/.test(String(value || ""));
}

function parseDateArg(value, endOfDay = false) {
  if (!value) {
    return 0;
  }

  const isoValue = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? `${value}T${endOfDay ? "23:59:59" : "00:00:00"}`
    : value;
  const timestamp = Date.parse(isoValue);

  if (Number.isNaN(timestamp)) {
    throw new Error(`Invalid date: ${value}. Use YYYY-MM-DD`);
  }

  return Math.floor(timestamp / 1000);
}

function messageTimestamp(message) {
  if (message.date instanceof Date) {
    return Math.floor(message.date.getTime() / 1000);
  }

  return Number(message.date || 0);
}

function serializeMessage(message) {
  return {
    id: message.id,
    date: message.date,
    senderId: message.senderId && String(message.senderId),
    replyToTopId:
      message.replyTo &&
      pick(message.replyTo.replyToTopId, message.replyTo.reply_to_top_id),
    replyToMsgId:
      message.replyTo &&
      pick(message.replyTo.replyToMsgId, message.replyTo.reply_to_msg_id),
    message: message.message || "",
  };
}

function messageToMarkdown(message) {
  const text = String(message.message || "").trim();
  if (!text) {
    return "";
  }

  return text;
}

function writeOutput(out, messages, format) {
  if (format === "md" || format === "markdown") {
    const markdown = messages
      .map(messageToMarkdown)
      .filter(Boolean)
      .join("\n\n---\n\n");

    fs.writeFileSync(out, markdown, "utf8");
    return;
  }

  fs.writeFileSync(out, JSON.stringify(messages, null, 2), "utf8");
}

async function findForumTopics(client, channel, query) {
  if (isIntegerString(query)) {
    const response = await client.invoke(
      new Api.channels.GetForumTopicsByID({
        channel,
        topics: [Number(query)],
      })
    );

    return response.topics || [];
  }

  const topics = [];
  let offsetDate = 0;
  let offsetId = 0;
  let offsetTopic = 0;

  while (true) {
    const response = await client.invoke(
      new Api.channels.GetForumTopics({
        channel,
        q: query,
        offsetDate,
        offsetId,
        offsetTopic,
        limit: 100,
      })
    );

    const batch = response.topics || [];
    if (!batch.length) {
      break;
    }

    topics.push(...batch);

    if (topics.length >= response.count || batch.length < 100) {
      break;
    }

    const lastTopic = batch[batch.length - 1];
    offsetDate = pick(lastTopic.date, 0);
    offsetId = topicMessageId(lastTopic) || 0;
    offsetTopic = topicId(lastTopic) || 0;
  }

  return topics;
}

function shouldKeepMessage(message, dateRange) {
  const timestamp = messageTimestamp(message);

  if (dateRange.since && timestamp < dateRange.since) {
    return false;
  }
  if (dateRange.until && timestamp > dateRange.until) {
    return false;
  }

  return true;
}

function topicRootIds(topics) {
  return new Set(
    topics
      .flatMap((topic) => [topicId(topic), topicMessageId(topic)])
      .filter((value) => value !== undefined && value !== null)
      .map(Number)
  );
}

function messageBelongsToTopic(message, topic, allTopics = []) {
  const replyTo = message.replyTo || {};
  const replyToTopId = pick(replyTo.replyToTopId, replyTo.reply_to_top_id);
  const replyToMsgId = pick(replyTo.replyToMsgId, replyTo.reply_to_msg_id);
  const id = Number(topicId(topic));
  const topMessage = Number(topicMessageId(topic));
  const currentRootIds = new Set([id, topMessage]);
  const otherRootIds = topicRootIds(
    allTopics.filter((oneTopic) => !currentRootIds.has(Number(topicId(oneTopic))))
  );

  if (otherRootIds.has(Number(message.id))) {
    return false;
  }
  if (message.id === id || message.id === topMessage) {
    return true;
  }
  if (otherRootIds.has(Number(replyToTopId)) || otherRootIds.has(Number(replyToMsgId))) {
    return false;
  }
  if (Number(replyToTopId) === id || Number(replyToTopId) === topMessage) {
    return true;
  }

  // Telegram's general forum topic is often id=1 and may not have reply headers.
  if (id === 1 || topMessage === 1) {
    return (
      !replyToTopId ||
      Number(replyToTopId) === 1 ||
      Number(replyToMsgId) === 1
    );
  }

  return false;
}

async function exportTopicMessages(client, peer, topic, limit, dateRange) {
  const messages = [];
  const topicMsgId = topicMessageId(topic);
  let offsetId = 0;

  while (limit <= 0 || messages.length < limit) {
    const batchLimit = limit > 0 ? Math.min(100, limit - messages.length) : 100;
    const response = await client.invoke(
      new Api.messages.GetReplies({
        peer,
        msgId: topicMsgId,
        offsetId,
        offsetDate: 0,
        addOffset: 0,
        limit: batchLimit,
        maxId: 0,
        minId: 0,
        hash: 0,
      })
    );

    const batch = response.messages || [];
    if (!batch.length) {
      break;
    }

    for (const message of batch) {
      if (dateRange.since && messageTimestamp(message) < dateRange.since) {
        return messages;
      }
      if (shouldKeepMessage(message, dateRange)) {
        messages.push(serializeMessage(message));
      }
    }

    offsetId = batch[batch.length - 1].id;

    if (messages.length % 1000 === 0) {
      console.log(`Saved in memory: ${messages.length}`);
    }
  }

  return messages;
}

async function exportTopicMessagesByHistoryScan(
  client,
  peer,
  topic,
  allTopics,
  limit,
  dateRange
) {
  const messages = [];
  let scanned = 0;
  let lastMatchedLog = 0;

  for await (const message of client.iterMessages(peer, { waitTime: 2 })) {
    scanned += 1;

    if (dateRange.since && messageTimestamp(message) < dateRange.since) {
      break;
    }
    if (
      shouldKeepMessage(message, dateRange) &&
      messageBelongsToTopic(message, topic, allTopics)
    ) {
      messages.push(serializeMessage(message));
    }

    if (messages.length && messages.length % 1000 === 0 && messages.length !== lastMatchedLog) {
      lastMatchedLog = messages.length;
      console.log(`Saved in memory: ${messages.length}`);
    }
    if (scanned % 5000 === 0) {
      console.log(`Scanned ${scanned}, matched ${messages.length}`);
    }
    if (limit > 0 && messages.length >= limit) {
      break;
    }
  }

  return messages;
}

async function exportTopicMessagesBySearch(client, peer, topic, limit, dateRange) {
  const messages = [];
  const topicMsgId = topicMessageId(topic);
  let offsetId = 0;

  while (limit <= 0 || messages.length < limit) {
    const batchLimit = limit > 0 ? Math.min(100, limit - messages.length) : 100;
    const response = await client.invoke(
      new Api.messages.Search({
        peer,
        q: "",
        topMsgId: topicMsgId,
        filter: new Api.InputMessagesFilterEmpty(),
        minDate: dateRange.since,
        maxDate: dateRange.until,
        offsetId,
        addOffset: 0,
        limit: batchLimit,
        maxId: 0,
        minId: 0,
        hash: 0,
      })
    );

    const batch = response.messages || [];
    if (!batch.length) {
      break;
    }

    for (const message of batch) {
      messages.push(serializeMessage(message));
    }

    offsetId = batch[batch.length - 1].id;

    if (messages.length % 1000 === 0) {
      console.log(`Saved in memory: ${messages.length}`);
    }
  }

  return messages;
}

async function main() {
  const positionalQuery = process.argv.slice(2).find((arg) => !arg.startsWith("--"));
  const link = parseTelegramPrivateLink(positionalQuery || getArg("chat"));
  const query = link ? link.chatId : positionalQuery || getArg("chat");
  const limit = Number(getArg("limit", "0"));
  const topicQuery = getArg("topic") || (link && link.topicOrMessageId);
  const listTopics = process.argv.includes("--list-topics");
  const requestedFormat = normalize(getArg("format", ""));
  const dateRange = {
    since: parseDateArg(getArg("since")),
    until: parseDateArg(getArg("until"), true),
  };

  if (!query) {
    console.error(
      "Usage: node export-chat.js <chat title | @username | id> [--topic=Topic] [--list-topics] [--limit=1000] [--format=json|md] [--out=messages.json]"
    );
    process.exit(1);
  }

  await auth();

  const client = api.getClient();
  const dialogs = await client.getDialogs({});
  const matches = dialogs.filter((dialog) => dialogMatches(dialog, query));

  if (!matches.length) {
    console.error(`Chat not found: ${query}`);
    console.error("Available chats:");
    dialogs
      .slice(0, 50)
      .forEach((dialog) => console.error(`- ${dialog.title} (${dialog.id})`));
    process.exit(1);
  }

  if (matches.length > 1) {
    console.error(`Found ${matches.length} chats. Use a more specific title or id:`);
    matches.forEach((dialog) => console.error(`- ${dialog.title} (${dialog.id})`));
    process.exit(1);
  }

  const dialog = matches[0];
  const out =
    getArg("out") ||
    path.join(
      "exports",
      `${safeFileName(dialog.title || query)}${
        topicQuery ? `_${safeFileName(topicQuery)}` : ""
      }.json`
    );
  const format =
    requestedFormat ||
    (path.extname(out).toLowerCase() === ".md" ? "md" : "json");

  fs.mkdirSync(path.dirname(out), { recursive: true });

  let messages = [];

  if (topicQuery || listTopics) {
    const allTopics = await findForumTopics(client, dialog.entity, "");
    let topics = allTopics;

    if (topicQuery && isIntegerString(topicQuery)) {
      topics = allTopics.filter((topic) => String(topicId(topic)) === String(topicQuery));
      if (!topics.length) {
        topics = await findForumTopics(client, dialog.entity, topicQuery);
      }
    }

    if (listTopics) {
      console.log(`Topics in "${dialog.title}":`);
      allTopics.forEach((topic) =>
        console.log(
          `- ${topicTitle(topic)} (${topicId(topic)}), topMessage=${topicMessageId(topic)}`
        )
      );
      await client.disconnect();
      return;
    }

    const topicMatchesList = topics.filter((topic) => topicMatches(topic, topicQuery));

    if (!topicMatchesList.length) {
      console.error(`Topic not found: ${topicQuery}`);
      console.error("Available matching topics:");
      topics.forEach((topic) =>
        console.error(
          `- ${topicTitle(topic)} (${topicId(topic)}), topMessage=${topicMessageId(topic)}`
        )
      );
      process.exit(1);
    }

    if (topicMatchesList.length > 1) {
      console.error(`Found ${topicMatchesList.length} topics. Use a more specific title or id:`);
      topicMatchesList.forEach((topic) =>
        console.error(
          `- ${topicTitle(topic)} (${topicId(topic)}), topMessage=${topicMessageId(topic)}`
        )
      );
      process.exit(1);
    }

    const topic = topicMatchesList[0];
    console.log(`Exporting topic "${topicTitle(topic)}" from "${dialog.title}"`);
    try {
      messages = await exportTopicMessages(
        client,
        dialog.entity,
        topic,
        limit,
        dateRange
      );
    } catch (error) {
      if (error && error.errorMessage === "TOPIC_ID_INVALID") {
        console.log("GetReplies failed for this topic, trying topic search instead");
        messages = await exportTopicMessagesBySearch(
          client,
          dialog.entity,
          topic,
          limit,
          dateRange
        );
        if (!messages.length) {
          console.log("Topic search returned 0 messages, scanning chat history instead");
          messages = await exportTopicMessagesByHistoryScan(
            client,
            dialog.entity,
            topic,
            allTopics,
            limit,
            dateRange
          );
        }
      } else {
        throw error;
      }
    }
  } else {
    const options = {};
    if (limit > 0) {
      options.limit = limit;
    }
    if (dateRange.since) {
      options.minId = 0;
    }

    for await (const message of client.iterMessages(dialog.entity, options)) {
      if (dateRange.since && messageTimestamp(message) < dateRange.since) {
        break;
      }
      if (shouldKeepMessage(message, dateRange)) {
        messages.push(serializeMessage(message));
      }

      if (messages.length % 1000 === 0) {
        console.log(`Saved in memory: ${messages.length}`);
      }
    }
  }

  writeOutput(out, messages, format);
  console.log(
    `Exported ${messages.length} messages from "${dialog.title}" to ${out} (${format})`
  );
  await client.disconnect();
}

main().catch(async (error) => {
  console.error(error);
  try {
    await api.getClient().disconnect();
  } catch (_) {
    // Ignore disconnect errors while exiting after the original failure.
  }
  process.exit(1);
});
