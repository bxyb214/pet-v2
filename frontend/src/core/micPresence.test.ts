import { beforeEach, describe, expect, it, vi } from "vitest";
import { holdMic, micActive, resetMicForTest, stopMic } from "./micPresence";

describe("micPresence", () => {
  beforeEach(() => resetMicForTest());

  it("默认没有麦克风占用", () => {
    expect(micActive.value).toBe(false);
  });

  it("登记后显示，释放后隐藏", () => {
    const release = holdMic(() => {});
    expect(micActive.value).toBe(true);
    release();
    expect(micActive.value).toBe(false);
  });

  it("多个占用者：全部释放后才隐藏", () => {
    const a = holdMic(() => {});
    const b = holdMic(() => {});
    a();
    expect(micActive.value).toBe(true);
    b();
    expect(micActive.value).toBe(false);
  });

  it("关闭麦克风会调用全部 stop；重复释放无副作用", () => {
    const stopA = vi.fn();
    const stopB = vi.fn();
    const a = holdMic(stopA);
    holdMic(stopB);

    stopMic();
    expect(stopA).toHaveBeenCalledTimes(1);
    expect(stopB).toHaveBeenCalledTimes(1);

    a();
    a();
    expect(micActive.value).toBe(true); // 另一个仍占用
  });
});
