/**
 * Realtime 握手回归：Offer 必须带音频 m 线（否则服务端 400 SDP format and content error），
 * 麦克风只能通过 replaceTrack 挂到已协商的 transceiver 上（不重新协商）。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const OFFER_SDP =
  "v=0\r\no=- 1 1 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n";
const ANSWER_SDP = "v=0\r\no=- 2 2 IN IP4 0.0.0.0\r\ns=-\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n";

class FakePC {
  static last: FakePC | null = null;
  static dcState: RTCDataChannelState = "open";
  order: string[] = [];
  sender = {
    replaceTrack: vi.fn(async (_t: unknown) => {
      this.order.push("replaceTrack");
    }),
  };
  transceiver = { sender: this.sender };
  dc = {
    readyState: FakePC.dcState,
    send: vi.fn((raw: string) => {
      this.order.push(`send:${(JSON.parse(raw) as { type?: string }).type ?? "?"}`);
    }),
    close: vi.fn(),
    onmessage: null as ((e: MessageEvent) => void) | null,
    onopen: null as (() => void) | null,
  };
  ontrack: ((ev: RTCTrackEvent) => void) | null = null;
  addTransceiver = vi.fn((kind: string) => {
    this.order.push(`addTransceiver:${kind}`);
    return this.transceiver;
  });
  createDataChannel = vi.fn(() => {
    this.order.push("createDataChannel");
    return this.dc;
  });
  createOffer = vi.fn(async () => {
    this.order.push("createOffer");
    return { type: "offer", sdp: OFFER_SDP } as RTCSessionDescriptionInit;
  });
  setLocalDescription = vi.fn(async () => undefined);
  setRemoteDescription = vi.fn(async () => undefined);
  getSenders = vi.fn(() => [] as RTCRtpSender[]);
  close = vi.fn();
  /** 模拟 ICE/DTLS 完成、数据通道 open */
  openDc(): void {
    this.dc.readyState = "open";
    this.dc.onopen?.();
  }
  constructor() {
    FakePC.last = this;
  }
}

class FakeAudio {
  autoplay = false;
  srcObject: unknown = null;
  play = vi.fn(async () => undefined);
  pause = vi.fn();
}

class FakeAudioContext {
  destination = {};
  createMediaStreamSource = vi.fn(() => ({ connect: vi.fn() }));
  createAnalyser = vi.fn(() => ({
    fftSize: 0,
    connect: vi.fn(),
    getByteTimeDomainData: vi.fn(),
  }));
  resume = vi.fn(async () => undefined);
  close = vi.fn(async () => undefined);
}

function jsonResponse(data: unknown): Response {
  return { ok: true, status: 200, json: async () => data } as Response;
}

const track = { enabled: true, stop: vi.fn() };
const stream = {
  getAudioTracks: () => [track],
  getTracks: () => [track],
};

const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
  const url = String(input);
  if (url.endsWith("/healthz")) return jsonResponse({ dev_mode: false });
  if (url.endsWith("/speak/sdp")) {
    return jsonResponse({
      sdp: ANSWER_SDP,
      voice: "Tina",
      vad: "semantic_vad",
      session_id: 9,
      max_session_sec: 300,
    });
  }
  throw new Error("unexpected fetch " + url);
});

const secureDescriptor = Object.getOwnPropertyDescriptor(window, "isSecureContext");
const mediaDescriptor = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");

beforeEach(() => {
  FakePC.last = null;
  FakePC.dcState = "open";
  Object.defineProperty(window, "isSecureContext", { value: true, configurable: true });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn(async () => stream) },
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("RTCPeerConnection", FakePC);
  vi.stubGlobal("Audio", FakeAudio);
  vi.stubGlobal("AudioContext", FakeAudioContext);
});

afterEach(() => {
  vi.unstubAllGlobals();
  if (secureDescriptor) Object.defineProperty(window, "isSecureContext", secureDescriptor);
  if (mediaDescriptor) Object.defineProperty(navigator, "mediaDevices", mediaDescriptor);
  else delete (navigator as { mediaDevices?: unknown }).mediaDevices;
});

/** 动态导入：每个用例拿到同一模块，但避免顶层 import 先于 mock 生效的问题 */
async function connect(mode: "shadow" | "talk") {
  const { createSpeakConn } = await import("./speakRTC");
  return createSpeakConn({
    mode,
    turnDetection: mode === "talk" ? "vad" : "manual",
    instructions: "transcribe one sentence",
    onStatus: () => undefined,
    onUserTranscript: () => undefined,
    onReply: () => undefined,
    onError: () => undefined,
  });
}

function sdpRequestBody(): Record<string, unknown> {
  const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/speak/sdp"));
  expect(call).toBeTruthy();
  return JSON.parse(String((call?.[1] as RequestInit | undefined)?.body));
}

describe("createSpeakConn SDP 协商", () => {
  it("Offer 先加上音频收发，再把浏览器 SDP 原样转给服务端", async () => {
    const conn = await connect("shadow");
    const pc = FakePC.last;
    expect(pc).not.toBeNull();
    // 顺序：先声明 m=audio，再建数据通道，最后 createOffer
    expect(pc?.order.slice(0, 3)).toEqual([
      "addTransceiver:audio",
      "createDataChannel",
      "createOffer",
    ]);

    const body = sdpRequestBody();
    expect(body.sdp).toBe(OFFER_SDP);
    expect(body.mode).toBe("shadow");
    expect(conn.sessionId).toBe(9);
    expect(conn.maxSessionSec).toBe(300);
    conn.close();
  });

  it("麦克风通过 replaceTrack 挂到已协商的 transceiver，session 配置先于音频下发", async () => {
    const conn = await connect("shadow");
    const pc = FakePC.last;

    await vi.waitFor(() => expect(pc?.sender.replaceTrack).toHaveBeenCalledWith(track));
    // 顺序：先 session.update（手动模式关掉自动轮次），再挂麦克风
    expect(pc?.order).toEqual([
      "addTransceiver:audio",
      "createDataChannel",
      "createOffer",
      "send:session.update",
      "replaceTrack",
    ]);
    const sessionUpdate = JSON.parse(String(pc?.dc.send.mock.calls[0][0]));
    expect(sessionUpdate.session.turn_detection).toBeNull();

    conn.close();
  });

  it("数据通道还在 connecting 时先排队，open 后补发 session.update", async () => {
    FakePC.dcState = "connecting";
    const conn = await connect("shadow");
    const pc = FakePC.last;

    await vi.waitFor(() => expect(pc?.sender.replaceTrack).toHaveBeenCalledWith(track));
    expect(pc?.dc.send).not.toHaveBeenCalled();
    expect(pc?.order).not.toContain("send:session.update");

    pc?.openDc();
    expect(pc?.dc.send).toHaveBeenCalledTimes(1);
    const sent = JSON.parse(String(pc?.dc.send.mock.calls[0][0]));
    expect(sent.type).toBe("session.update");

    conn.close();
  });
});
