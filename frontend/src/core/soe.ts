/**
 * 腾讯智聆口语评测（新版）客户端：后端拿签名 WSS URL，前端直连音频流。
 * 接口要求（doc 1774/107497）：16kHz / 16bit / 单声道 PCM，voice_format=0，
 * 建议每 40ms 发 1280 字节（1:1 实时率），结束发 {"type":"end"} 文本帧。
 */
import { api } from "./api";
import { ensureDevMode } from "./devMode";
import { holdMic } from "./micPresence";
import { micBlockedReason, micErrorText } from "./micSupport";

export type SoeWord = { w: string; ok: boolean };
export type SoeResult = { score: number; words: SoeWord[] };

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
  /** 评测结束（拿到结果、超时或出错）自动 stop 后回调一次，页面据此复位按钮 */
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

type SoeWordRaw = { Word?: unknown; PronAccuracy?: unknown };

function toNum(v: unknown): number {
  if (typeof v === "number") return Number.isFinite(v) ? v : NaN;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

/**
 * 解析 SOE 结果。新版服务实际返回结构化对象：
 * { SuggestedScore, PronAccuracy, Words: [{ Word, PronAccuracy, ... }] }；
 * 旧文档/兼容格式是类 Python dict 文本，两种都支持。
 */
export function parseSoeResult(raw: unknown): SoeResult {
  if (raw && typeof raw === "object") {
    const obj = raw as { SuggestedScore?: unknown; PronAccuracy?: unknown; Words?: unknown };
    let score = toNum(obj.SuggestedScore);
    const pron = toNum(obj.PronAccuracy);
    if (!(score >= 0)) score = pron >= 0 ? pron : NaN;
    const words: SoeWord[] = [];
    const accs: number[] = [];
    const list = Array.isArray(obj.Words) ? obj.Words : [];
    for (const item of list) {
      if (!item || typeof item !== "object") continue;
      const word = item as SoeWordRaw;
      const w = String(word.Word ?? "").trim();
      const acc = toNum(word.PronAccuracy);
      if (w && acc >= 0) {
        words.push({ w, ok: acc >= 60 });
        accs.push(acc);
      }
    }
    if (!(score >= 0) && accs.length) score = Math.max(...accs);
    return { score: score >= 0 ? Math.round(score) : 0, words };
  }

  const text = typeof raw === "string" ? raw : "";
  const num = (field: string): number => {
    const m = text.match(new RegExp(`${field}:(-?[\\d.]+)`));
    return m ? parseFloat(m[1]) : NaN;
  };
  let score = num("SuggestedScore");
  const pron = num("PronAccuracy");
  if (!(score >= 0)) score = pron >= 0 ? pron : NaN;
  const words: SoeWord[] = [];
  const accs: number[] = [];
  const wordsPart = text.split("Words:")[1] ?? "";
  for (const chunk of wordsPart.split("{").slice(1)) {
    const body = chunk.split("}")[0];
    const w = body.match(/Word:([^\s}]+)/)?.[1];
    const acc = parseFloat(body.match(/PronAccuracy:(-?[\d.]+)/)?.[1] ?? "NaN");
    if (w && acc >= 0) {
      words.push({ w, ok: acc >= 60 });
      accs.push(acc);
    }
  }
  if (!(score >= 0) && accs.length) score = Math.max(...accs);
  return { score: score >= 0 ? Math.round(score) : 0, words };
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
   * 采集开始后登记麦克风占用：数字人出现，底部按钮显示「提交」。
   * 点击提交：已经开口就结束录音并评分；还没开口则提示继续朗读，不结束会话。
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
    }, { label: "提交", tone: "submit" });
  }

  private releaseMicHold(): void {
    const release = this.releaseMic;
    this.releaseMic = null;
    release?.();
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
      this.opts.onStatus("开发环境：模拟评测就绪，读完点「提交」");
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
    this.opts.onStatus("在听你说…读完点「提交」");
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
        const result = { score: 100, words: words.length ? words : [{ w: "Great", ok: true }] };
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
