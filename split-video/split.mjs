import { execSync, spawnSync } from "child_process";
import { basename, join, dirname } from "path";

const input = process.argv[2];
if (!input) {
  console.error("Usage: node split.mjs <video-file>");
  process.exit(1);
}

const SEGMENT_SEC = 9 * 60;
const FFMPEG = process.env.LOCALAPPDATA + "\\Microsoft\\WinGet\\Links\\ffmpeg.exe";

const probe = spawnSync(FFMPEG, ["-i", input], { encoding: "utf-8" });
const output = (probe.stdout || "") + (probe.stderr || "");
const match = output.match(/Duration:\s*(\d+):(\d+):(\d+)/);
if (!match) {
  console.error("Could not determine video duration");
  process.exit(1);
}
const totalSec = +match[1] * 3600 + +match[2] * 60 + +match[3];
const parts = Math.ceil(totalSec / SEGMENT_SEC);

console.log(`Duration: ${match[1]}:${match[2]}:${match[3]} (${totalSec}s)`);
console.log(`Splitting into ${parts} parts of ${SEGMENT_SEC}s each...\n`);

const name = basename(input, ".mp4");
const dir = dirname(input);

for (let i = 0; i < parts; i++) {
  const start = i * SEGMENT_SEC;
  const out = join(dir, `${name}_part${i + 1}.mp4`);
  console.log(`Part ${i + 1}/${parts}  start=${start}s -> ${out}`);
  execSync(
    `"${FFMPEG}" -y -ss ${start} -i "${input}" -t ${SEGMENT_SEC} -c copy "${out}"`,
    { stdio: "inherit", shell: true }
  );
}

console.log("\nDone!");
