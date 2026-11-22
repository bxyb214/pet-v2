/**
 * 「绿野成长」v3 主题：tokens.css 语义 → Naive UI themeOverrides（类型安全）。
 * 一处改全局生效；与 tokens.css 保持同源数值。
 * 主色维持 #16a34a（白字按钮需 ≥18px 加粗）；文字/链接用 #15803d 保证 4.5:1。
 */
import type { GlobalThemeOverrides } from "naive-ui";

const FONT = '"Nunito", system-ui, "PingFang SC", "Microsoft YaHei", sans-serif';

export const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#16a34a",
    primaryColorHover: "#15803d",
    primaryColorPressed: "#166534",
    primaryColorSuppl: "#15803d",
    infoColor: "#2563eb",
    warningColor: "#d97706",
    errorColor: "#dc2626",
    successColor: "#16a34a",
    borderRadius: "14px",
    borderRadiusSmall: "10px",
    fontFamily: FONT,
    fontSize: "15px",
    fontSizeMedium: "15px",
    fontSizeLarge: "16px",
    fontWeightStrong: "700",
    bodyColor: "#16211c",
    textColorBase: "#16211c",
    textColor1: "#16211c",
    textColor2: "#3d4f45",
    textColor3: "#64756c",
    borderColor: "#e6eee9",
    dividerColor: "#eef4f0",
    cardColor: "#ffffff",
    modalColor: "#ffffff",
    popoverColor: "#ffffff",
    tableColor: "#ffffff",
    tableHeaderColor: "#fafdfb",
    hoverColor: "rgba(22, 163, 74, 0.07)",
    boxShadow1: "0 1px 2px rgba(16,40,28,.04), 0 4px 12px rgba(16,40,28,.05)",
    boxShadow2: "0 2px 6px rgba(16,40,28,.06), 0 12px 28px rgba(16,40,28,.08)",
    boxShadow3: "0 8px 20px rgba(16,40,28,.10), 0 24px 48px rgba(16,40,28,.12)",
  },
  Card: {
    borderRadius: "20px",
    borderColor: "#e6eee9",
  },
  Button: {
    borderRadiusMedium: "14px",
    borderRadiusSmall: "10px",
    borderRadiusTiny: "8px",
    fontWeight: "600",
    fontWeightStrong: "700",
  },
  Tabs: {
    tabFontWeightActive: "700",
  },
  Menu: {
    itemBorderRadius: "12px",
    itemHeight: "42px",
    fontSize: "14.5px",
  },
  DataTable: {
    borderRadius: "20px",
    thFontWeight: "600",
  },
  Tag: {
    borderRadius: "8px",
  },
  Progress: {
    railColor: "#e9f2ec",
  },
  Input: {
    borderRadius: "12px",
  },
  Radio: {
    buttonBorderRadius: "10px",
  },
};
