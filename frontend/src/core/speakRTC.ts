/**
 * Qwen Realtime WebRTC 客户端（精简移植自旧站 speak.js 核心流程）。
 * 约束：先协商收发，session.updated 后再挂麦克风（push-to-talk 可设）。
 */
import { api } from "./api";
import { ensureDevMode } from "./devMode";
import { createDevSpeakConn } from "./devSpeak";
import { holdMic } from "./micPresence";

export type SpeakMsg = Record<string, unknown> & { type: string };

export type SpeakConnOpts = {
  mode: "shadow" | "talk";
  instructions: string;
  turnDetection: "manual" | "vad";
  /** 服务端配置的轮次检测类型；manual 模式忽略 */
  vad?: string;
  /** AI 说话时暂停麦克风轨道（P2-1），默认开启 */
  halfDuplex?: boolean;
  onStatus: (s: string) => void;
  onUserTranscript: (t: string) => void;
  /** shadow：评测 JSON 文本；talk：AI 回复文本 */
  onReply: (t: string) => void;
  onError: (msg: string) => void;
  /** talk：模型调用 hint 工具时，屏幕弹出中文提示卡 */
  onHint?: (text: string) => void;
  /** talk：模型调用 praise 工具时，屏幕显示奖励 */
  onPraise?: (text: string) => void;
  /** 用户点数字人下的「关闭麦克风」：先回调页面清理状态，再由 core 关闭连接 */
  onMicClosed?: () => void;
};

export type SpeakConn = {
  send: (m: SpeakMsg) => void;
  close: () => void;
  /** 手动提交缓冲（shadow 模式），instr 为评测提示词 */
  commitAndRespond: (instr?: string) => void;
  /** 复用连接时更新提示词（P1-5：不再重新 SDP 握手） */
  updateInstructions?: (instr: string) => void;
  ready: boolean;
  closed: boolean;
  /** 会话已持续秒数（记账上报用） */
  elapsedSec: () => number;
  /** 孩子真正开口的累计秒数（本地麦克风能量检测） */
  speechSec: () => number;
  /** 服务端返回的会话上限与剩余额度（P0-1） */
  sessionId?: number;
  maxSessionSec?: number;
};

// talk 模式客户端工具：屏幕提示卡 + 奖励（§5 屏幕辅助区）
const TALK_TOOLS = [
  {
    type: "function",
    name: "hint",
    description:
      "Show a short Chinese hint card on the student's screen when they are stuck. Use it together with your spoken hint. Keep text under 40 Chinese characters.",
    parameters: {
      type: "object",
      properties: { text: { type: "string", description: "简短中文提示，可含一个英文关键词" } },
      required: ["text"],
    },
  },
  {
    type: "function",
    name: "praise",
    description: "Show a small praise/sticker on the student's screen after a good answer.",
    parameters: {
      type: "object",
      properties: { text: { type: "string", description: "中文夸奖，10 字以内" } },
      required: ["text"],
    },
  },
];

function parseSdpError(raw: string): string {
  try {
    const j = JSON.parse(raw);
    return j.detail || j.message || j.error?.message || raw;
  } catch {
    return raw;
  }
}

export async function createSpeakConn(opts: SpeakConnOpts): Promise<SpeakConn> {
  // 开发/测试环境：不建立 WebRTC，用脚本化对话跑通页面
  if (await ensureDevMode()) return createDevSpeakConn(opts);

  const pc = new RTCPeerConnection({ iceServers: [] });
  const startedAt = Date.now();
  let speechMs = 0;
  let meter: ReturnType<typeof setInterval> | null = null;
  /** AI 说话期间暂停的本地麦克风轨道（P2-1 半双工） */
  let micTracks: MediaStreamTrack[] = [];
  const halfDuplex = opts.halfDuplex !== false;
  const setMicEnabled = (on: boolean): void => {
    if (!halfDuplex) return;
    for (const tr of micTracks) {
      try { tr.enabled = on; } catch { /* noop */ }
    }
  };
  let meterCtx: AudioContext | null = null;
  /** 麦克风占用登记；关闭连接时释放，数字人随之消失 */
  let releaseMic: (() => void) | null = null;
  const dc = pc.createDataChannel("oai-events");
  const conn: SpeakConn & { text: string; lastReply: string } = {
    ready: false,
    text: "",
    lastReply: "",
    elapsedSec: () => Math.max(0, Math.round((Date.now() - startedAt) / 1000)),
    speechSec: () => Math.round(speechMs / 1000),
    updateInstructions(instr: string) {
      opts.instructions = instr;
      applySession(instr);
      // 复用连接时清掉上一轮残留音频，避免带入下一句
      conn.send({ type: "input_audio_buffer.clear" });
    },
    send(m) {
      if (dc.readyState === "open") dc.send(JSON.stringify(m));
    },
    commitAndRespond(instr) {
      conn.send({ type: "input_audio_buffer.commit" });
      conn.send({
        type: "response.create",
        response: instr ? { modalities: ["text"], instructions: instr } : { modalities: ["text"] },
      });
      setTimeout(() => {
        try { if (!conn.closed) conn.send({ type: "input_audio_buffer.clear" }); } catch { /* noop */ }
      }, 600);
    },
    close() {
      conn.closed = true;
      releaseMic?.();
      releaseMic = null;
      if (meter) clearInterval(meter);
      meter = null;
      try { void meterCtx?.close(); } catch { /* noop */ }
      meterCtx = null;
      try { pc.getSenders().forEach((s) => s.track?.stop()); } catch { /* noop */ }
      try { dc.close(); } catch { /* noop */ }
      try { pc.close(); } catch { /* noop */ }
    },
    closed: false,
  };

  // 消息处理
  dc.onmessage = (e) => {
    let d: SpeakMsg;
    try { d = JSON.parse(e.data); } catch { return; }
    const t = d.type;
    if (t === "session.updated" || t === "session.created") {
      if (!conn.ready) {
        conn.ready = true;
        opts.onStatus("已连接，可以开始");
      }
      return;
    }
    if (t === "input_audio_buffer.speech_started") {
      if (opts.mode === "talk") opts.onStatus("在听你说…");
      return;
    }
    if (t === "response.created") {
      conn.text = "";
      setMicEnabled(false); // AI 开始说话 → 暂停输入，减少回声与输入音频
      if (opts.mode === "talk") opts.onStatus("AI 正在想…");
      return;
    }
    if (t === "response.text.delta" || t === "response.audio_transcript.delta") {
      conn.text += String((d as { delta?: string }).delta ?? "");
      return;
    }
    if (t === "response.text.done" || t === "response.audio_transcript.done") {
      const full = String((d as { text?: string; transcript?: string }).text
        ?? (d as { transcript?: string }).transcript ?? conn.text ?? "");
      if (full) { opts.onReply(full); }
      return;
    }
    if (t === "conversation.item.input_audio_transcription.completed") {
      const text = String((d as { transcript?: string }).transcript ?? "");
      if (text) opts.onUserTranscript(text);
      return;
    }
    if (t === "response.function_call_arguments.done") {
      const name = String((d as { name?: string }).name ?? "");
      const callId = String((d as { call_id?: string }).call_id ?? "");
      let args: { text?: string } = {};
      try {
        args = JSON.parse(String((d as { arguments?: string }).arguments ?? "{}"));
      } catch { /* noop */ }
      const text = String(args.text ?? "").slice(0, 120);
      if (name === "hint" && text) opts.onHint?.(text);
      if (name === "praise" && text) opts.onPraise?.(text);
      // 回填工具结果并继续（否则模型会停在这里等）
      if (callId) {
        conn.send({
          type: "conversation.item.create",
          item: { type: "function_call_output", call_id: callId, output: JSON.stringify({ ok: true }) },
        });
        conn.send({ type: "response.create" });
      }
      return;
    }
    if (t === "response.done") {
      setMicEnabled(true);
      if (conn.text && opts.mode === "talk") opts.onReply(conn.text);
      if (opts.mode === "talk") opts.onStatus("轮到你了");
      conn.text = "";
      return;
    }
    if (t === "error") {
      setMicEnabled(true);
      const em = (d as { error?: { message?: string; code?: string } }).error ?? {};
      const msg = em.message || em.code || "语音服务返回错误";
      if (/buffer|duration|exceed/i.test(msg)) {
        conn.send({ type: "input_audio_buffer.clear" });
        opts.onStatus("刚才没录上，请再读一遍");
        return;
      }
      opts.onError(msg);
    }
  };

  // SDP 协商
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  opts.onStatus("连接语音服务…");
  let answer: string;
  let gotVoice = "";
  try {
    const r = await api<{
      sdp: string; voice: string; vad?: string; session_id?: number; max_session_sec?: number;
    }>("/speak/sdp", {
      method: "POST",
      body: JSON.stringify({
        sdp: offer.sdp,
        mode: opts.mode,
        instructions_chars: opts.instructions.length,
      }),
    });
    answer = r.sdp;
    gotVoice = r.voice;
    conn.sessionId = r.session_id;
    conn.maxSessionSec = r.max_session_sec;
    if (r.vad) opts.vad = r.vad;
  } catch (err) {
    const e = err as { message?: string; status?: number };
    pc.close();
    throw new Error(parseSdpError(e.message ?? "连接失败"));
  }
  await pc.setRemoteDescription({ type: "answer", sdp: answer });

  /** 下发/更新会话配置；同一连接切换句子时只改 instructions（P1-5） */
  const applySession = (instructions: string): void => {
    const vad = opts.vad || "semantic_vad";
    conn.send({
      type: "session.update",
      session: {
        voice: gotVoice,
        instructions,
        turn_detection:
          opts.turnDetection === "vad" && opts.vad !== "none" ? { type: vad } : null,
        ...(opts.mode === "talk" ? { tools: TALK_TOOLS, tool_choice: "auto" } : {}),
      },
    });
  };

  // session.updated 后挂麦克风并下发 session 配置
  const attach = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      stream.getTracks().forEach((tr) => pc.addTrack(tr, stream));
      micTracks = stream.getAudioTracks();
      // 麦克风真正拿到后才登记：数字人只在采集期间出现
      releaseMic = holdMic(() => {
        opts.onMicClosed?.();
        conn.close();
        if (!opts.onMicClosed) opts.onStatus("麦克风已关闭");
      });
      // 本地能量检测：只累计孩子真正开口的时长（AI 声音被回声消除过滤）
      try {
        meterCtx = new AudioContext();
        const meterSrc = meterCtx.createMediaStreamSource(stream);
        const analyser = meterCtx.createAnalyser();
        analyser.fftSize = 512;
        meterSrc.connect(analyser);
        const buf = new Uint8Array(analyser.fftSize);
        void meterCtx.resume();
        meter = setInterval(() => {
          analyser.getByteTimeDomainData(buf);
          let sum = 0;
          for (let i = 0; i < buf.length; i++) {
            const v = (buf[i] - 128) / 128;
            sum += v * v;
          }
          if (Math.sqrt(sum / buf.length) > 0.02) speechMs += 200;
        }, 200);
      } catch { /* 环境不支持能量检测时只记 0 秒 */ }
      applySession(opts.instructions);
      opts.onStatus(opts.mode === "talk" ? "准备好就开口吧" : "点「开始朗读」");
    } catch {
      releaseMic?.();
      releaseMic = null;
      opts.onError("无法访问麦克风，请检查浏览器权限");
    }
  };
  void attach();

  return conn;
}
