/**
 * 造句页本地录音（V11 流程重做）：替代原 WebRTC/Realtime 单轮转写。
 * 只做三件事：拿麦克风 + MediaRecorder 出 Blob、能量检测算开口秒数、
 * 登记 holdMic 让数字人面板显示「提交 / 取消」。评分/转写都在页面与后端。
 */
import { ensureDevMode } from "./devMode";
import { holdMic } from "./micPresence";
import { micBlockedReason, micErrorText } from "./micSupport";

export type MakeRec = {
  /** 结束录音并交出 Blob；重复调用返回同一个结果（幂等） */
  stop: () => Promise<Blob | null>;
  /** 孩子真正开口的累计秒数（本地能量检测） */
  speechSec: () => number;
  /** 放弃本次录音：停麦克风采音、丢掉 Blob（提交失败兜底用） */
  close: () => void;
};

export function pickRecorderType(): string | undefined {
  try {
    return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((t) =>
      MediaRecorder.isTypeSupported(t),
    );
  } catch {
    return undefined;
  }
}

/** 开发环境：不碰麦克风，给一个脚本化 MakeRec（数字人交互与页面逻辑可完整跑通） */
function devRec(opts: {
  onStatus: (s: string) => void;
  onSubmit?: () => void;
  onCancel?: () => void;
}): MakeRec {
  const startedAt = Date.now();
  let stopped = false;
  const release = holdMic(
    () => {
      if (opts.onSubmit) {
        opts.onSubmit();
        return;
      }
      stopped = true;
      opts.onStatus("麦克风已关闭");
    },
    { label: "提交", tone: "submit", cancelLabel: "取消" },
    () => {
      if (opts.onCancel) opts.onCancel();
      stopped = true;
    },
  );
  return {
    stop() {
      stopped = true;
      release();
      return Promise.resolve(null);
    },
    speechSec() {
      return stopped ? 0 : Math.max(0, Math.round((Date.now() - startedAt) / 1000));
    },
    close() {
      stopped = true;
      release();
    },
  };
}

/**
 * 开启录音。数字人「提交」由页面接管（opts.onSubmit：页面判断开口秒数后调
 * rec.stop() 走转写）；「取消」→ opts.onCancel（页面清状态，录音丢弃）。
 */
export async function startMakeRecording(opts: {
  onStatus: (s: string) => void;
  onError: (msg: string) => void;
  /** 数字人「提交」：页面接管（不传则只停采音，不结束录制） */
  onSubmit?: () => void;
  /** 数字人「取消」：放弃本次录音 */
  onCancel?: () => void;
}): Promise<MakeRec> {
  if (await ensureDevMode()) return devRec(opts);

  const blocked = micBlockedReason();
  if (blocked) {
    opts.onError(blocked);
    throw new Error(blocked);
  }
  opts.onStatus("开启麦克风…");
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch (e) {
    const msg = micErrorText(e);
    opts.onError(msg);
    throw new Error(msg);
  }

  const type = pickRecorderType();
  let recorder: MediaRecorder | null = null;
  const chunks: BlobPart[] = [];
  let takePromise: Promise<Blob | null> | null = null;
  try {
    recorder = type ? new MediaRecorder(stream, { mimeType: type }) : new MediaRecorder(stream);
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };
    recorder.start();
  } catch {
    recorder = null;
  }

  // 能量检测：累计真正开口的秒数（「还没听到声音」判断与练习时长）
  let speechMs = 0;
  let ctx: AudioContext | null = null;
  let meter: ReturnType<typeof setInterval> | null = null;
  try {
    ctx = new AudioContext();
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    void ctx.resume();
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

  const stopInput = (): void => {
    if (meter) clearInterval(meter);
    meter = null;
    try { void ctx?.close(); } catch { /* noop */ }
    ctx = null;
    try { stream.getTracks().forEach((t) => t.stop()); } catch { /* noop */ }
  };

  const release = holdMic(
    () => {
      // 数字人「提交」：页面接管提交流程；页面没接管时兜底只停采音。
      if (opts.onSubmit) {
        opts.onSubmit();
        return;
      }
      stopInput();
    },
    { label: "提交", tone: "submit", cancelLabel: "取消" },
    () => {
      if (opts.onCancel) {
        opts.onCancel();
        return;
      }
      stopInput();
    },
  );

  return {
    stop() {
      if (!takePromise) {
        const rec = recorder;
        if (!rec || rec.state === "inactive") {
          takePromise = Promise.resolve(null);
        } else {
          takePromise = new Promise<Blob | null>((resolve) => {
            rec.onstop = () => {
              const t = rec.mimeType || "audio/webm";
              resolve(chunks.length ? new Blob(chunks, { type: t }) : null);
              stopInput();
              release();
            };
            try { rec.stop(); } catch { resolve(null); }
          });
        }
      }
      return takePromise;
    },
    speechSec() {
      return Math.round(speechMs / 1000);
    },
    close() {
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        try { recorder.stop(); } catch { /* noop */ }
      }
      recorder = null;
      stopInput();
      release();
    },
  };
}
