const fs = require("fs");

const inputFile = process.argv[2] || "exports/om_valutnye_obschenie.json";
const outputFile =
  process.argv[3] || inputFile.replace(/\.json$/i, ".md");

const messages = JSON.parse(fs.readFileSync(inputFile, "utf8"));
const markdown = messages
  .map((item) => String(item.message || "").trim())
  .filter(Boolean)
  .join("\n\n---\n\n");

fs.writeFileSync(outputFile, markdown, "utf8");

console.log(`Converted ${messages.length} JSON items to ${outputFile}`);
