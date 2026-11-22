/**
 * Qwen Realtime WebRTC 客户端（精简移植自旧站 speak.js 核心流程）。
 * 约束：先协商收发，session.updated 后再挂麦克风（push-to-talk 可设）。
 */
import { api } from "./api";

export type SpeakMsg = Record<string, unknown> & { type: string };

export type SpeakConnOpts = {
  mode: "shadow" | "talk";
  instructions: string;
  turnDetection: "manual" | "vad";
  onStatus: (s: string) => void;
  onUserTranscript: (t: string) => void;
  /** shadow：评测 JSON 文本；talk：AI 回复文本 */
  onReply: (t: string) => void;
  onError: (msg: string) => void;
  /** talk：模型调用 hint 工具时，屏幕弹出中文提示卡 */
  onHint?: (text: string) => void;
  /** talk：模型调用 praise 工具时，屏幕显示奖励 */
  onPraise?: (text: string) => void;
};

export type SpeakConn = {
  send: (m: SpeakMsg) => void;
  close: () => void;
  /** 手动提交缓冲（shadow 模式），instr 为评测提示词 */
  commitAndRespond: (instr?: string) => void;
  ready: boolean;
  closed: boolean;
  /** 会话已持续秒数（记账上报用） */
  elapsedSec: () => number;
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
  const pc = new RTCPeerConnection({ iceServers: [] });
  const startedAt = Date.now();
  const dc = pc.createDataChannel("oai-events");
  const conn: SpeakConn & { text: string; lastReply: string } = {
    ready: false,
    text: "",
    lastReply: "",
    elapsedSec: () => Math.max(0, Math.round((Date.now() - startedAt) / 1000)),
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
    if (t === "response.created") { conn.text = ""; if (opts.mode === "talk") opts.onStatus("AI 正在想…"); return; }
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
      if (conn.text && opts.mode === "talk") opts.onReply(conn.text);
      if (opts.mode === "talk") opts.onStatus("轮到你了");
      conn.text = "";
      return;
    }
    if (t === "error") {
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
    const r = await api<{ sdp: string; voice: string }>("/speak/sdp", {
      method: "POST",
      body: JSON.stringify({ sdp: offer.sdp, mode: opts.mode }),
    });
    answer = r.sdp;
    gotVoice = r.voice;
  } catch (err) {
    const e = err as { message?: string; status?: number };
    pc.close();
    throw new Error(parseSdpError(e.message ?? "连接失败"));
  }
  await pc.setRemoteDescription({ type: "answer", sdp: answer });

  // session.updated 后挂麦克风并下发 session 配置
  const attach = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      stream.getTracks().forEach((tr) => pc.addTrack(tr, stream));
      conn.send({
        type: "session.update",
        session: {
          voice: gotVoice,
          instructions: opts.instructions,
          // qwen3.8 Realtime 支持 semantic_vad：过滤附和声/背景音，减少误触发
          turn_detection:
            opts.turnDetection === "vad" ? { type: "semantic_vad" } : null,
          ...(opts.mode === "talk" ? { tools: TALK_TOOLS, tool_choice: "auto" } : {}),
        },
      });
      opts.onStatus(opts.mode === "talk" ? "准备好就开口吧" : "点「开始朗读」");
    } catch {
      opts.onError("无法访问麦克风，请检查浏览器权限");
    }
  };
  void attach();

  return conn;
}
