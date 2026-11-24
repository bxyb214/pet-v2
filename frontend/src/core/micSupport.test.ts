import { describe, expect, it } from "vitest";
import { micBlockedReason, micErrorText } from "./micSupport";

describe("micBlockedReason", () => {
  it("非安全上下文提示改用 HTTPS", () => {
    const desc = Object.getOwnPropertyDescriptor(window, "isSecureContext");
    Object.defineProperty(window, "isSecureContext", { value: false, configurable: true });
    expect(micBlockedReason()).toContain("HTTPS");
    if (desc) Object.defineProperty(window, "isSecureContext", desc);
  });

  it("安全上下文且支持 getUserMedia 时不拦截", () => {
    const desc = Object.getOwnPropertyDescriptor(window, "isSecureContext");
    Object.defineProperty(window, "isSecureContext", { value: true, configurable: true });
    const md = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: () => Promise.resolve() },
      configurable: true,
    });
    expect(micBlockedReason()).toBe("");
    if (desc) Object.defineProperty(window, "isSecureContext", desc);
    if (md) Object.defineProperty(navigator, "mediaDevices", md);
    else delete (navigator as { mediaDevices?: unknown }).mediaDevices;
  });
});

describe("micErrorText", () => {
  it("按 DOMException.name 给出具体原因", () => {
    expect(micErrorText({ name: "NotAllowedError" })).toContain("权限被拒绝");
    expect(micErrorText({ name: "NotFoundError" })).toContain("没有检测到麦克风");
    expect(micErrorText({ name: "NotReadableError" })).toContain("占用");
    expect(micErrorText(new Error("x"))).toContain("没有拿到麦克风");
    expect(micErrorText(null)).toContain("没有拿到麦克风");
  });
});
