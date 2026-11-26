import { beforeEach, describe, expect, it, vi } from "vitest";
import { resetDevModeForTest } from "./devMode";
import { pickRecorderType, startMakeRecording } from "./makeRecorder";
import { resetMicForTest, stopMic, cancelMic } from "./micPresence";

describe("pickRecorderType", () => {
  it("不支持 MediaRecorder 时返回 undefined（jsdom 无 isTypeSupported）", () => {
    // jsdom 没有 MediaRecorder：find 回调里访问会抛错，兜底返回 undefined
    expect(pickRecorderType()).toBeUndefined();
  });
});

describe("startMakeRecording（开发环境模拟链路）", () => {
  beforeEach(() => {
    resetMicForTest();
    resetDevModeForTest();
    vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
      // api() 请求带 /api/v1 前缀；healthz 也可能带 BASE
      if (String(url).includes("healthz")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: "ok", dev_mode: true }),
        });
      }
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }));
  });

  it("dev 模式：不出真实麦克风但登记数字人，stop/close 幂等", async () => {
    const rec = await startMakeRecording({ onStatus: vi.fn(), onError: vi.fn() });
    expect(rec.speechSec()).toBeGreaterThanOrEqual(0);

    const b1 = await rec.stop();
    const b2 = await rec.stop();
    expect(b1).toBeNull();
    expect(b2).toBeNull(); // 幂等

    rec.close();
    rec.close(); // 重复 close 不抛
  });

  it("数字人「提交」由页面接管（onSubmit），「取消」走 onCancel", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    await startMakeRecording({ onStatus: vi.fn(), onError: vi.fn(), onSubmit, onCancel });

    stopMic();
    expect(onSubmit).toHaveBeenCalledTimes(1);

    cancelMic();
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledTimes(1); // 取消不触发提交
  });

  it("没传 onSubmit 时数字人提交只回落到关闭", async () => {
    const onStatus = vi.fn();
    await startMakeRecording({ onStatus, onError: vi.fn() });
    stopMic();
    expect(onStatus).toHaveBeenCalledWith("麦克风已关闭");
  });
});
