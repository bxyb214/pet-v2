/**
 * 腾讯智聆口语评测（新版）客户端：后端拿签名 WSS URL，前端直连音频流。
 * 接口要求（doc 1774/107497）：16kHz / 16bit / 单声道 PCM，voice_format=0，
 * 建议每 40ms 发 1280 字节（1:1 实时率），结束发 {"type":"end"} 文本帧。
 */
import { api } from "./api";
import { ensureDevMode } from "./devMode";
import { holdMic } from "./micPresence";

export type SoeWord = { w: string; ok: boolean };
export type SoeResult = { score: number; words: SoeWord[] };

export type SoeOpts = {
  refText: string;
  onStatus: (s: string) => void;
  onResult: (r: SoeResult) => void;
  onError: (msg: string) => void;
  /** 结果字符串解析器（测试可注入）；默认 parseSoeResult */
  parser?: (raw: string) => SoeResult;
  /** 用户点数字人下的「关闭麦克风」：先回调页面清理状态，再由 SoeEval 停止采集 */
  onMicClosed?: () => void;
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

/** 解析 SOE 返回的类 Python dict 结果文本（SuggestedScore/PronAccuracy/Words）。 */
export function parseSoeResult(raw: string): SoeResult {
  const num = (field: string): number => {
    const m = raw.match(new RegExp(`${field}:(-?[\\d.]+)`));
    return m ? parseFloat(m[1]) : NaN;
  };
  let score = num("SuggestedScore");
  const pron = num("PronAccuracy");
  if (!(score >= 0)) score = pron >= 0 ? pron : NaN;
  const words: SoeWord[] = [];
  const accs: number[] = [];
  const wordsPart = raw.split("Words:")[1] ?? "";
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
  private pending = new Int16Array(0);
  private timer: ReturnType<typeof setInterval> | null = null;
  private closed = false;
  private final = false;
  private parser: (raw: string) => SoeResult;
  private lastResult: SoeResult | null = null;
  private speechMs = 0;
  private dev = false;
  private devStartedAt = 0;
  private releaseMic: (() => void) | null = null;

  constructor(private opts: SoeOpts) {
    this.parser = opts.parser ?? parseSoeResult;
  }

  /** 采集开始后登记麦克风占用：数字人出现，按钮关闭时停止采集 */
  private attachMicHold(): void {
    this.releaseMic?.();
    this.releaseMic = holdMic(() => {
      this.opts.onMicClosed?.();
      this.stop();
      if (!this.opts.onMicClosed) this.opts.onStatus("麦克风已关闭");
    });
  }

  /** 请求签名 URL 并建立 WebSocket + 麦克风采集。 */
  async start(): Promise<void> {
    // 开发/测试环境：不请求签名 URL、不连腾讯 SOE，提交时直接给满分
    this.dev = await ensureDevMode();
    if (this.dev) {
      this.devStartedAt = Date.now();
      this.attachMicHold();
      this.opts.onStatus("开发环境：模拟评测就绪，读完点「提交」");
      return;
    }
    this.opts.onStatus("连接评测服务…");
    let url: string;
    try {
      const r = await api<{ url: string }>("/speak/soe_url", {
        method: "POST",
        body: JSON.stringify({ ref_text: this.opts.refText, eval_mode: 1 }),
      });
      url = r.url;
    } catch (e) {
      this.opts.onError((e as Error).message || "评测服务未配置");
      throw e;
    }
    const ws = new WebSocket(url);
    this.ws = ws;
    ws.onmessage = (ev) => {
      if (typeof ev.data !== "string") return;
      let d: { code?: number; message?: string; result?: string; final?: number };
      try { d = JSON.parse(ev.data); } catch { return; }
      if ((d.code ?? 0) !== 0) {
        this.opts.onError(d.message || `评测错误 ${d.code}`);
        return;
      }
      if (d.result) {
        const r = this.parser(d.result);
        if (r.score > 0 || r.words.length) this.lastResult = r;
      }
      if (d.final === 1) {
        this.final = true;
        this.opts.onStatus("评测完成");
        if (this.lastResult) this.opts.onResult(this.lastResult);
        this.stop();
      }
    };
    ws.onerror = () => {
      if (!this.closed) this.opts.onError("评测连接出错，请重试");
    };
    await new Promise<void>((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = () => reject(new Error("评测连接失败"));
    });

    // 麦克风 16k 采集
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.attachMicHold();
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
    // 40ms 一包（16k → 640 样本 = 1280 字节）
    this.timer = setInterval(() => this.flush(), 40);
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
    }
    const merged = new Int16Array(this.pending.length + chunk.length);
    merged.set(this.pending);
    merged.set(chunk, this.pending.length);
    this.pending = merged;
  }

  /** 孩子真正开口的累计秒数（本地能量检测；开发环境按练习时长计） */
  speechSec(): number {
    if (this.dev) return Math.max(0, Math.round((Date.now() - this.devStartedAt) / 1000));
    return Math.round(this.speechMs / 1000);
  }

  /** 按 1280 字节分包发送，单次 tick 最多 3 包（服务端 1s 内最多收 3s 音频）。 */
  private flush(): void {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    let packs = 0;
    const samplesPerPack = 640;
    while (this.pending.length >= samplesPerPack && packs < 3) {
      ws.send(this.pending.slice(0, samplesPerPack).buffer);
      this.pending = this.pending.slice(samplesPerPack);
      packs++;
    }
  }

  /** 提交：刷完剩余音频 + 发 end，等待 final 结果。 */
  submit(): void {
    if (this.dev) {
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
      return;
    }
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    while (this.pending.length > 0) {
      const pack = this.pending.slice(0, 640);
      ws.send(pack.buffer);
      this.pending = this.pending.slice(pack.length);
    }
    ws.send(JSON.stringify({ type: "end" }));
    this.opts.onStatus("评分中…");
    // 服务端 15s 超时兜底
    setTimeout(() => {
      if (!this.final && !this.closed) {
        this.opts.onError("评测超时，请重试");
        this.stop();
      }
    }, 12000);
  }

  stop(): void {
    this.closed = true;
    this.releaseMic?.();
    this.releaseMic = null;
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
  }
}
