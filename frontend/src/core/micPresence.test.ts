import { beforeEach, describe, expect, it, vi } from "vitest";
import { cancelMic, holdMic, micAction, micActive, resetMicForTest, stopMic } from "./micPresence";

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

  it("跟读评分登记「提交」按钮文案，释放后恢复默认", () => {
    expect(micAction.value.label).toBe("关闭麦克风");
    const release = holdMic(() => {}, { label: "提交", tone: "submit" });
    expect(micAction.value).toEqual({ label: "提交", tone: "submit" });
    release();
    expect(micAction.value.label).toBe("关闭麦克风");
    expect(micAction.value.tone).toBe("close");
  });

  it("「取消」单独回调，不会触发提交", () => {
    const stop = vi.fn();
    const cancel = vi.fn();
    holdMic(stop, { label: "提交", tone: "submit", cancelLabel: "取消" }, cancel);
    expect(micAction.value.cancelLabel).toBe("取消");
    cancelMic();
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(stop).not.toHaveBeenCalled();

    stopMic();
    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("没登记取消时沿用 stop（关闭麦克风即停止）", () => {
    const stop = vi.fn();
    holdMic(stop);
    cancelMic();
    expect(stop).toHaveBeenCalledTimes(1);
  });
});
