/**
 * 腾讯智聆口语评测（新版）客户端：后端拿签名 WSS URL，前端直连音频流。
 * 接口要求（doc 1774/107497）：16kHz / 16bit / 单声道 PCM，voice_format=0，
 * 建议每 40ms 发 1280 字节（1:1 实时率），结束发 {"type":"end"} 文本帧。
 */
import { api } from "./api";
import { ensureDevMode } from "./devMode";
import { holdMic } from "./micPresence";
import { micBlockedReason, micErrorText } from "./micSupport";

export type SoeWord = { w: string; ok: boolean; acc?: number; tag?: number };
export type SoeResult = {
  /** 综合建议分（0-100） */
  score: number;
  /** 发音准确度（0-100）；腾讯没返回时为 null */
  accuracy: number | null;
  /** 发音流利度（0-100）；腾讯按 0-1 返回时已换算成百分制 */
  fluency: number | null;
  /** 发音完整度（0-100） */
  completion: number | null;
  words: SoeWord[];
};

export type SoeOpts = {
  refText: string;
  onStatus: (s: string) => void;
  onResult: (r: SoeResult) => void;
  onError: (msg: string) => void;
  /** 结果解析器（测试可注入）；默认 parseSoeResult，兼容对象与文本两种格式 */
  parser?: (raw: unknown) => SoeResult;
  /** 用户点数字人下的「提交」：页面清理提示；SOE 已结束录音并提交评分 */
  onMicClosed?: () => void;
  /** 提交后进入上传/评分阶段（true），拿到结果/出错/取消后复位（false） */
  onBusy?: (busy: boolean) => void;
  /** 评测结束（拿到结果、超时、出错或取消）自动 stop 后回调一次，页面据此复位按钮 */
  onStopped?: () => void;
};

const WORKLET_SRC = `
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) this.port.postMessage(Float32Array.from(ch));
    return true;
  }
}
registerProcessor("pcm-capture", PcmCapture);
`;

function floatToInt16(f32: Float32Array): Int16Array {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

/**
 * 裁掉首尾静音（每侧留 300ms 余量），缩短 1:1 上传的等待时间。
 * 全静音时原样返回（提交前已有开口检测，这里只做兜底）。
 */
export function trimSilence(audio: Int16Array, marginMs = 300): Int16Array {
  const win = 320; // 20ms
  const threshold = 0.02;
  let first = -1;
  let last = -1;
  for (let i = 0; i + win <= audio.length; i += win) {
    let sum = 0;
    for (let j = i; j < i + win; j++) {
      const v = audio[j] / 32768;
      sum += v * v;
    }
    if (Math.sqrt(sum / win) > threshold) {
      if (first < 0) first = i;
      last = i + win;
    }
  }
  if (first < 0) return audio;
  const pad = Math.round((marginMs / 1000) * 16000);
  const start = Math.max(0, first - pad);
  const end = Math.min(audio.length, last + pad);
  return start === 0 && end === audio.length ? audio : audio.slice(start, end);
}

type SoeWordRaw = { Word?: unknown; PronAccuracy?: unknown; MatchTag?: unknown; Tag?: unknown };

function toNum(v: unknown): number {
  if (typeof v === "number") return Number.isFinite(v) ? v : NaN;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

/** 0-100 的分值；负数表示腾讯「无法评分」，按缺失处理。 */
function toScore(v: number): number | null {
  return Number.isFinite(v) && v >= 0 ? Math.min(100, Math.round(v)) : null;
}

/** 腾讯的流利度/完整度按 0-1 返回（新版本也可能是 0-100），统一成百分制。 */
function toPercent(v: number): number | null {
  if (!Number.isFinite(v) || v < 0) return null;
  return Math.round(v <= 1.5 ? v * 100 : v);
}

/** MatchTag：0 匹配 / 1 增读 / 2 漏读 / 3 替换 / 4 无法识别。 */
function parseWord(raw: SoeWordRaw): SoeWord | null {
  const w = String(raw.Word ?? "").trim();
  if (!w) return null;
  const acc = toNum(raw.PronAccuracy);
  const tagNum = toNum(raw.MatchTag ?? raw.Tag ?? NaN);
  const accOk = acc >= 0 ? Math.min(100, Math.round(acc)) : undefined;
  const tag = Number.isFinite(tagNum) ? tagNum : undefined;
  if (accOk === undefined && tag === undefined) return null;
  // 漏读/增读/替换都算没读对；只有匹配（tag=0 或无 tag）且准确度 ≥60 才算过
  const ok = (tag === undefined || tag === 0) && (accOk ?? 0) >= 60;
  const out: SoeWord = { w, ok };
  if (accOk !== undefined) out.acc = accOk;
  if (tag !== undefined) out.tag = tag;
  return out;
}

function parseResultObject(raw: Record<string, unknown>): SoeResult {
  // 段落模式可能把逐句结果放在 Sentences 里；单句缺顶层字段时回落到第一句
  const sentences = Array.isArray(raw.Sentences) ? raw.Sentences : [];
  const first = sentences[0];
  const inner = first && typeof first === "object" ? (first as Record<string, unknown>) : {};
  const wordsRaw =
    Array.isArray(raw.Words) && raw.Words.length
      ? raw.Words
      : Array.isArray(inner.Words)
        ? inner.Words
        : [];
  const accuracy = toScore(toNum(raw.PronAccuracy ?? inner.PronAccuracy));
  let score = toNum(raw.SuggestedScore ?? inner.SuggestedScore);
  const words = wordsRaw
    .map((item) => (item && typeof item === "object" ? parseWord(item as SoeWordRaw) : null))
    .filter((w): w is SoeWord => w !== null);
  if (!(score >= 0)) score = accuracy ?? NaN;
  if (!(score >= 0) && words.length) score = Math.max(...words.map((w) => w.acc ?? 0));
  return {
    score: score >= 0 ? Math.min(100, Math.round(score)) : 0,
    accuracy,
    fluency: toPercent(toNum(raw.PronFluency ?? inner.PronFluency)),
    completion: toPercent(toNum(raw.PronCompletion ?? inner.PronCompletion)),
    words,
  };
}

/**
 * 解析 SOE 结果。新版服务实际返回结构化对象：
 * { SuggestedScore, PronAccuracy, PronFluency, PronCompletion,
 *   Words: [{ Word, PronAccuracy, MatchTag, ... }] }；
 * 旧文档/兼容格式是类 Python dict 文本，两种都支持。
 */
export function parseSoeResult(raw: unknown): SoeResult {
  if (raw && typeof raw === "object") return parseResultObject(raw as Record<string, unknown>);

  const text = typeof raw === "string" ? raw : "";
  const num = (field: string): number => {
    const m = text.match(new RegExp(`${field}:\\s*(-?[\\d.]+)`));
    return m ? parseFloat(m[1]) : NaN;
  };
  const accuracy = toScore(num("PronAccuracy"));
  let score = num("SuggestedScore");
  const words: SoeWord[] = [];
  const wordsPart = text.split("Words:")[1] ?? "";
  for (const chunk of wordsPart.split("{").slice(1)) {
    const body = chunk.split("}")[0];
    const word = parseWord({
      Word: body.match(/Word:\s*([^\s}]+)/)?.[1],
      PronAccuracy: body.match(/PronAccuracy:\s*(-?[\d.]+)/)?.[1],
      MatchTag: body.match(/MatchTag:\s*(\d+)/)?.[1] ?? body.match(/\bTag:\s*(\d+)/)?.[1],
    });
    if (word) words.push(word);
  }
  if (!(score >= 0)) score = accuracy ?? NaN;
  if (!(score >= 0) && words.length) score = Math.max(...words.map((w) => w.acc ?? 0));
  return {
    score: score >= 0 ? Math.min(100, Math.round(score)) : 0,
    accuracy,
    fluency: toPercent(num("PronFluency")),
    completion: toPercent(num("PronCompletion")),
    words,
  };
}

function nameList(words: SoeWord[]): string {
  const names = [...new Set(words.map((w) => w.w).filter(Boolean))];
  return names.length > 4 ? `${names.slice(0, 4).join("、")} 等` : names.join("、");
}

/** 由评分维度生成可执行的改进提示（结果页展示，也作为练习记录的评价内容）。 */
export function soeTips(r: SoeResult): string[] {
  const tips: string[] = [];
  const missed = r.words.filter((w) => w.tag === 2);
  const extra = r.words.filter((w) => w.tag === 1);
  const swapped = r.words.filter((w) => w.tag === 3);
  const bad = r.words.filter((w) => !w.ok && w.tag !== 1 && w.tag !== 2 && w.tag !== 3);
  if (missed.length) tips.push(`漏读了 ${nameList(missed)}，跟着示范逐词读完整，别跳词。`);
  if (swapped.length) tips.push(`这几个词读成了别的词：${nameList(swapped)}，先听示范再跟读。`);
  if (extra.length) tips.push(`多读了 ${nameList(extra)}，只读屏幕上的词就好。`);
  if (bad.length) tips.push(`重点练 ${nameList(bad)}：点词听发音，慢速读三遍再连起来。`);

  // 三项分维度合成一条：分数低才提，并给对应练法
  const lows: string[] = [];
  const advice: string[] = [];
  if (r.accuracy !== null && r.accuracy < 70) {
    lows.push(`准确度 ${r.accuracy} 分`);
    advice.push("放慢速度，注意词尾的 s/ed 和长元音");
  }
  if (r.fluency !== null && r.fluency < 70) {
    lows.push(`流利度 ${r.fluency} 分`);
    advice.push("听一遍示范，再连着读 3 遍，注意连读和停顿");
  }
  if (r.completion !== null && r.completion < 80) {
    lows.push(`完整度 ${r.completion} 分`);
    advice.push("有词没读出来，先把整句读全，再追求速度");
  }
  if (lows.length) tips.push(`${lows.join(" · ")}：${advice.join("；")}。`);

  if (!tips.length) {
    tips.push(
      r.score >= 85
        ? "读得很棒！可以再用正常语速读一遍，保持连读。"
        : "整体不错，再听一遍示范，注意句子的重音和停顿。",
    );
  }
  // 词级提示最多 3 条，保证维度建议不会被挤掉
  return tips.length > 4 && lows.length
    ? [...tips.slice(0, 3), tips[tips.length - 1]]
    : tips.slice(0, 4);
}

export class SoeEval {
  private ws: WebSocket | null = null;
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | ScriptProcessorNode | null = null;
  /** 录音期间的完整 PCM（提交时才连服务上传，避免长连接在朗读中途被断开） */
  private chunks: Int16Array[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private closed = false;
  private final = false;
  private parser: (raw: unknown) => SoeResult;
  private lastResult: SoeResult | null = null;
  private speechMs = 0;
  private dev = false;
  private devStartedAt = 0;
  private releaseMic: (() => void) | null = null;
  private stoppedNotified = false;
  private submitted = false;

  constructor(private opts: SoeOpts) {
    this.parser = opts.parser ?? parseSoeResult;
  }

  /**
   * 采集开始后登记麦克风占用：数字人出现，底部显示「提交」和「取消」。
   * 提交：已经开口就结束录音并评分；还没开口则提示继续朗读，不结束会话。
   * 取消：放弃本次录音，不提交评分，回到可重新开始的状态。
   */
  private attachMicHold(): void {
    this.releaseMic?.();
    this.releaseMic = holdMic(() => {
      if (this.closed) return;
      if (this.submitted) {
        // 已在等待结果：只收麦克风，等评分返回
        this.releaseMicHold();
        this.endCapture();
        return;
      }
      if (this.speechSec() <= 0) {
        this.opts.onStatus("还没听到声音，对着麦克风朗读一遍再点「提交」");
        return;
      }
      this.releaseMicHold();
      this.opts.onMicClosed?.();
      this.endCapture();
      if (!this.submit()) this.stop();
    }, { label: "提交", tone: "submit", cancelLabel: "取消" }, () => this.cancelRecording());
  }

  private releaseMicHold(): void {
    const release = this.releaseMic;
    this.releaseMic = null;
    release?.();
  }

  /** 数字人「取消」：结束录音但不评分，丢掉这次录音，回到可重新开始的状态。 */
  private cancelRecording(): void {
    if (this.closed) return;
    this.releaseMicHold();
    this.endCapture();
    this.stop();
    this.opts.onStatus("已取消本次跟读，点「跟读评分」重新开始");
  }

  /** 停止麦克风采集与音频上下文，但保留评测连接（提交后还要等结果）。 */
  private endCapture(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    try { this.node?.disconnect(); } catch { /* noop */ }
    this.node = null;
    try { this.ctx?.close(); } catch { /* noop */ }
    this.ctx = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
  }

  /** 开始采集：只拿麦克风并录音；评测连接推迟到「提交」时再建。 */
  async start(): Promise<void> {
    // 开发/测试环境：不请求签名 URL、不连腾讯 SOE，提交时直接给满分
    this.dev = await ensureDevMode();
    if (this.dev) {
      this.devStartedAt = Date.now();
      this.attachMicHold();
      this.opts.onStatus("开发环境：模拟评测就绪，读完点「提交」，想重读点「取消」");
      return;
    }
    // 先要麦克风权限：点按钮就弹授权，允许后出现数字人
    const blocked = micBlockedReason();
    if (blocked) {
      this.opts.onError(blocked);
      throw new Error(blocked);
    }
    this.opts.onStatus("请允许使用麦克风…");
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (e) {
      const msg = micErrorText(e);
      this.opts.onError(msg);
      throw new Error(msg);
    }
    this.attachMicHold();

    // 16k PCM 采集（麦克风已在前面拿到）
    this.ctx = new AudioContext({ sampleRate: 16000 });
    const src = this.ctx.createMediaStreamSource(this.stream);
    try {
      const blob = new Blob([WORKLET_SRC], { type: "application/javascript" });
      await this.ctx.audioWorklet.addModule(URL.createObjectURL(blob));
      const node = new AudioWorkletNode(this.ctx, "pcm-capture");
      node.port.onmessage = (ev) => this.enqueue(floatToInt16(ev.data as Float32Array));
      src.connect(node);
      this.node = node;
    } catch {
      // AudioWorklet 不可用 → ScriptProcessor 兜底
      const sp = this.ctx.createScriptProcessor(2048, 1, 1);
      sp.onaudioprocess = (ev) => this.enqueue(floatToInt16(new Float32Array(ev.inputBuffer.getChannelData(0))));
      src.connect(sp);
      sp.connect(this.ctx.destination);
      this.node = sp;
    }
    this.opts.onStatus("在听你说…读完点小绿下面的「提交」，读错可点「取消」");
  }

  private enqueue(chunk: Int16Array): void {
    if (chunk.length) {
      let sum = 0;
      for (let i = 0; i < chunk.length; i++) {
        const v = chunk[i] / 32768;
        sum += v * v;
      }
      if (Math.sqrt(sum / chunk.length) > 0.02) {
        this.speechMs += (chunk.length / 16000) * 1000;
      }
      this.chunks.push(chunk);
    }
  }

  /** 孩子真正开口的累计秒数（本地能量检测；开发环境按练习时长计） */
  speechSec(): number {
    if (this.dev) return Math.max(0, Math.round((Date.now() - this.devStartedAt) / 1000));
    return Math.round(this.speechMs / 1000);
  }

  private bindWs(ws: WebSocket): void {
    ws.onmessage = (ev) => {
      if (typeof ev.data !== "string") return;
      let d: { code?: number; message?: string; result?: unknown; final?: number };
      try { d = JSON.parse(ev.data); } catch { return; }
      if ((d.code ?? 0) !== 0) {
        this.opts.onError(d.message || `评测错误 ${d.code}`);
        this.stop();
        return;
      }
      if (d.result) {
        // 解析失败不能中断 final 处理（否则页面只能等到超时）
        try {
          const r = this.parser(d.result);
          if (r.score > 0 || r.words.length) this.lastResult = r;
        } catch {
          /* 忽略无法解析的中间结果 */
        }
      }
      if (d.final === 1) {
        this.final = true;
        this.opts.onStatus("评测完成");
        if (this.lastResult) {
          this.opts.onResult(this.lastResult);
        } else {
          this.opts.onError("没有拿到评分结果，请重试");
        }
        this.stop();
      }
    };
    ws.onerror = () => {
      if (!this.closed && !this.final) this.opts.onError("评测连接出错，请重试");
    };
    ws.onclose = () => {
      if (!this.closed && !this.final) {
        this.opts.onError("评测连接中断，请重试");
        this.stop();
      }
    };
  }

  /** 提交后：拿签名 URL → 连接 → 按 1:1 实时率上传整段录音 → end → 等结果。 */
  private async connectAndSend(): Promise<void> {
    const total = this.chunks.reduce((n, c) => n + c.length, 0);
    const raw = new Int16Array(total);
    let offset = 0;
    for (const c of this.chunks) {
      raw.set(c, offset);
      offset += c.length;
    }
    this.chunks = [];
    const audio = trimSilence(raw);

    let url: string;
    try {
      const r = await api<{ url: string }>("/speak/soe_url", {
        method: "POST",
        body: JSON.stringify({ ref_text: this.opts.refText, eval_mode: 1 }),
      });
      url = r.url;
    } catch (e) {
      if (!this.closed) {
        this.opts.onError((e as Error).message || "评测服务未配置");
        this.stop();
      }
      return;
    }
    if (this.closed) return;

    const ws = new WebSocket(url);
    this.ws = ws;
    this.bindWs(ws);
    try {
      await new Promise<void>((resolve, reject) => {
        const to = setTimeout(() => reject(new Error("评测连接超时，请重试")), 10000);
        ws.onopen = () => {
          clearTimeout(to);
          resolve();
        };
        ws.onerror = () => {
          clearTimeout(to);
          reject(new Error("评测连接失败，请重试"));
        };
      });
    } catch (e) {
      if (!this.closed) {
        this.opts.onError((e as Error).message);
        this.stop();
      }
      return;
    }
    if (this.closed) return;
    ws.onerror = () => {
      if (!this.closed && !this.final) this.opts.onError("评测连接出错，请重试");
    };
    this.uploadAudio(ws, audio);
  }

  /**
   * 腾讯要求 1:1 实时率（每 40ms 发 40ms 音频，即 640 样本 / 1280 字节）；
   * 发得比实时快可能让引擎出错或直接断开，所以按录音时长回放。
   */
  private uploadAudio(ws: WebSocket, audio: Int16Array): void {
    const pack = 640;
    let offset = 0;
    let lastPct = -1;
    this.opts.onStatus("上传录音… 0%");
    this.timer = setInterval(() => {
      if (this.closed) return;
      if (ws.readyState !== WebSocket.OPEN) return;
      if (offset < audio.length) {
        ws.send(audio.slice(offset, offset + pack).buffer);
        offset = Math.min(audio.length, offset + pack);
        const pct = Math.min(100, Math.floor((offset / audio.length) * 100));
        if (pct !== lastPct && (pct % 10 === 0 || offset >= audio.length)) {
          lastPct = pct;
          this.opts.onStatus(`上传录音… ${pct}%`);
        }
      }
      if (offset >= audio.length) {
        if (this.timer) clearInterval(this.timer);
        this.timer = null;
        ws.send(JSON.stringify({ type: "end" }));
        this.opts.onStatus("评分中…");
        // 评分等待窗口随录音长度放宽；服务端 15s 无响应时兜底
        const audioSec = Math.max(1, Math.round(audio.length / 16000));
        const waitMs = Math.max(20000, Math.min(45000, 10000 + audioSec * 1000));
        setTimeout(() => {
          if (!this.final && !this.closed) {
            this.opts.onError("评分超时，请重试");
            this.stop();
          }
        }, waitMs);
      }
    }, 40);
  }

  /** 提交：结束录音并连接评测服务；返回是否已进入评分。 */
  submit(): boolean {
    if (this.submitted) return true;
    if (this.closed) return false;
    if (this.dev) {
      this.submitted = true;
      this.opts.onBusy?.(true);
      this.releaseMicHold();
      this.endCapture();
      const words = this.opts.refText
        .split(/\s+/)
        .map((w) => w.replace(/[^\w'-]/g, ""))
        .filter(Boolean)
        .map((w) => ({ w, ok: true }));
      this.opts.onStatus("开发环境：模拟评分中…");
      setTimeout(() => {
        if (this.closed) return;
        this.final = true;
        const result: SoeResult = {
          score: 100,
          accuracy: 100,
          fluency: 100,
          completion: 100,
          words: words.length ? words : [{ w: "Great", ok: true }],
        };
        this.lastResult = result;
        this.opts.onStatus("评测完成");
        this.opts.onResult(result);
        this.stop();
      }, 500);
      return true;
    }
    if (!this.chunks.length) {
      this.opts.onStatus("还没听到声音，对着麦克风朗读一遍再点「提交」");
      return false;
    }
    this.submitted = true;
    this.opts.onBusy?.(true);
    this.releaseMicHold();
    this.endCapture();
    this.opts.onStatus("正在连接评测服务…");
    void this.connectAndSend();
    return true;
  }

  stop(): void {
    this.closed = true;
    this.opts.onBusy?.(false);
    this.releaseMicHold();
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    try { this.ws?.close(); } catch { /* noop */ }
    this.ws = null;
    try { this.node?.disconnect(); } catch { /* noop */ }
    this.node = null;
    try { this.ctx?.close(); } catch { /* noop */ }
    this.ctx = null;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    if (!this.stoppedNotified) {
      this.stoppedNotified = true;
      this.opts.onStopped?.();
    }
  }
}
