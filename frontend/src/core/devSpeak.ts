/**
 * 开发环境的 Realtime 模拟连接：不建立 WebRTC、不请求 Qwen。
 *
 * - shadow：点「提交」直接返回满分 JSON；
 * - talk：按脚本自动产生「孩子说一句 → AI 回一句」，让优化、计时、复盘整条链路可点通。
 */
import type { SpeakConn, SpeakConnOpts } from "./speakRTC";
import { holdMic } from "./micPresence";

const TALK_SCRIPT = [
  {
    user: "I like play football with my friends.",
    ai: "That sounds fun! Who do you usually play with?",
  },
  {
    user: "I play with my classmates after school.",
    ai: "Nice. Why do you enjoy football?",
  },
  {
    user: "Because it is exciting and I can run a lot.",
    ai: "Great answer! Do you also watch football matches?",
  },
];

export function parseDevTarget(instructions: string): string {
  const m = instructions.match(/Target sentence for shadowing:\s*"([^"]+)"/);
  return (m?.[1] ?? "I like learning English.").trim();
}

export function devShadowResult(instructions: string): {
  transcript: string;
  score: number;
  words: { w: string; ok: boolean }[];
  tips: string[];
  say: string;
} {
  const transcript = parseDevTarget(instructions);
  const words = transcript
    .split(/\s+/)
    .map((w) => w.replace(/[^\w'-]/g, ""))
    .filter(Boolean)
    .map((w) => ({ w, ok: true }));
  return {
    transcript,
    score: 100,
    words: words.length ? words : [{ w: "Great", ok: true }],
    tips: [],
    say: "Perfect! Keep going.",
  };
}

export function createDevSpeakConn(opts: SpeakConnOpts): SpeakConn {
  const startedAt = Date.now();
  const timers: number[] = [];
  let closed = false;
  let releaseMic: (() => void) | null = null;

  const later = (ms: number, fn: () => void): void => {
    timers.push(window.setTimeout(() => {
      if (!closed) fn();
    }, ms));
  };

  const conn: SpeakConn = {
    ready: true,
    closed: false,
    send() {
      /* 模拟连接不发送任何信令 */
    },
    commitAndRespond() {
      if (opts.mode !== "shadow") return;
      opts.onStatus("开发环境：模拟评分中…");
      later(450, () => {
        opts.onStatus("开发环境：模拟评分完成");
        opts.onReply(JSON.stringify(devShadowResult(opts.instructions)));
      });
    },
    close() {
      closed = true;
      conn.closed = true;
      releaseMic?.();
      releaseMic = null;
      timers.forEach((id) => window.clearTimeout(id));
      timers.length = 0;
    },
    elapsedSec: () => Math.max(0, Math.round((Date.now() - startedAt) / 1000)),
    speechSec: () => Math.max(0, Math.round((Date.now() - startedAt) / 1000)),
  };

  // 开发环境同样登记“麦克风占用”：数字人可测，文案会标明是模拟语音
  releaseMic = holdMic(() => {
    opts.onMicClosed?.();
    conn.close();
    if (!opts.onMicClosed) opts.onStatus("麦克风已关闭");
  });

  later(400, () => opts.onStatus("开发环境：模拟语音已连接"));

  if (opts.mode === "talk") {
    later(1200, () => opts.onReply("Hi! I'm Pip. What do you like doing at the weekend?"));

    let idx = 0;
    const turn = (): void => {
      const item = TALK_SCRIPT[idx % TALK_SCRIPT.length];
      idx += 1;
      opts.onUserTranscript(item.user);
      later(1100, () => opts.onReply(item.ai));
      later(5200, turn);
    };
    later(3000, turn);
  }

  return conn;
}
