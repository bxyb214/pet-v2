/**
 * 绿野成长 v2 主题：tokens.css 语义 → Naive UI themeOverrides（类型安全）。
 * 一处改全局生效；与 tokens.css 保持同源数值。
 */
import type { GlobalThemeOverrides } from "naive-ui";

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
    borderRadius: "10px",
    borderRadiusSmall: "8px",
    fontSize: "15px",
    fontSizeMedium: "15px",
    fontSizeLarge: "16px",
    bodyColor: "#1f2d26",
    textColorBase: "#1f2d26",
    textColor1: "#1f2d26",
    textColor2: "#3d4f45",
    textColor3: "#6b7f74",
    borderColor: "#dbe7df",
    dividerColor: "#e5efe9",
    cardColor: "#ffffff",
    modalColor: "#ffffff",
    popoverColor: "#ffffff",
    tableColor: "#ffffff",
    tableHeaderColor: "#fafdfb",
    hoverColor: "rgba(22, 163, 74, 0.08)",
  },
  Card: {
    borderRadius: "16px",
  },
  Button: {
    borderRadiusMedium: "10px",
    borderRadiusSmall: "8px",
    fontWeight: "600",
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
    borderRadius: "16px",
    thFontWeight: "600",
  },
  Tag: {
    borderRadius: "8px",
  },
};

/** 学科主题色（语文/数学占位用） */
export const SUBJECT_COLORS = {
  english: { bg: "#e7f6ec", color: "#15803d" },
  chinese: { bg: "#fef3c7", color: "#b45309" },
  math: { bg: "#dbeafe", color: "#1d4ed8" },
} as const;
