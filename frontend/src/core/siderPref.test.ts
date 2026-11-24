import { describe, expect, it } from "vitest";
import { isSiderCollapsed, parseSiderPref, SIDER_AUTO_WIDTH } from "./siderPref";

describe("侧栏折叠偏好", () => {
  it("没有手动偏好时按宽度：窄屏默认收起", () => {
    expect(isSiderCollapsed(SIDER_AUTO_WIDTH - 1, null)).toBe(true);
    expect(isSiderCollapsed(SIDER_AUTO_WIDTH, null)).toBe(false);
    expect(isSiderCollapsed(1440, null)).toBe(false);
  });

  it("平板竖屏默认收起，横屏/桌面默认展开", () => {
    expect(isSiderCollapsed(820, null)).toBe(true);
    expect(isSiderCollapsed(1024, null)).toBe(false);
  });

  it("手动展开后即使窄屏也保持展开", () => {
    expect(isSiderCollapsed(900, "open")).toBe(false);
  });

  it("手动收起后即使宽屏也保持收起", () => {
    expect(isSiderCollapsed(1600, "closed")).toBe(true);
  });

  it("只认 open / closed，其它值回到自动", () => {
    expect(parseSiderPref("open")).toBe("open");
    expect(parseSiderPref("closed")).toBe("closed");
    expect(parseSiderPref("1")).toBeNull();
    expect(parseSiderPref(null)).toBeNull();
  });
});
