import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../../apps/web/public/media");
const required = ["replaytutor-demo-en-poster.webp", "replaytutor-demo-zh-poster.webp", "replaytutor-demo-en.vtt", "replaytutor-demo-zh.vtt", "replaytutor-demo-readme.gif", "replaytutor-demo-zh-readme.gif"];
const optionalVideos = ["replaytutor-demo-en.mp4", "replaytutor-demo-zh.mp4"];
for (const file of required) {
  const info = await stat(resolve(root, file));
  if (file.endsWith(".gif") && info.size > 8 * 1024 * 1024) throw new Error(`${file} exceeds the 8 MB README budget`);
}
for (const file of optionalVideos) {
  try { const info = await stat(resolve(root, file)); if (info.size > 15 * 1024 * 1024) throw new Error(`${file} exceeds the 15 MB budget`); }
  catch (error) { if (error?.code !== "ENOENT") throw error; }
}
const recordingRoot = resolve(import.meta.dirname, "../public/recordings");
for (const [suffix, locale] of [["en", "en-US"], ["zh", "zh-CN"]]) {
  try {
    const manifest = JSON.parse(await readFile(resolve(recordingRoot, `replaytutor-browser-${suffix}.json`), "utf8"));
    if (manifest.locale !== locale) throw new Error(`${suffix} recording locale is ${manifest.locale}`);
    if (!Array.isArray(manifest.locale_checks) || manifest.locale_checks.length !== 3) throw new Error(`${suffix} recording is missing locale checks`);
    for (const check of manifest.locale_checks) {
      if (check.html_lang !== locale) throw new Error(`${suffix}/${check.scene} has html lang ${check.html_lang}`);
      if (locale === "en-US" && check.han_sample_count !== 0) throw new Error(`${suffix}/${check.scene} contains Chinese UI`);
      if (locale === "zh-CN" && check.han_sample_count < 1) throw new Error(`${suffix}/${check.scene} contains no Chinese UI`);
    }
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}
console.log("ReplayTutor demo assets verified");
