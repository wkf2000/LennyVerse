export const themeTokens = {
  colors: {
    primary: "#1B365D",
    accent: "#D77601",
    neutralDark: "#6A8EAE",
    neutralLight: "#EBE4D3",
    white: "#FFFFFF",
    text: "#1A1A2E",
  },
  typography: {
    headingFamily: '"Noto Serif", Georgia, serif',
    bodyFamily: '"Noto Sans", system-ui, -apple-system, Segoe UI, sans-serif',
    monoFamily: '"DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
  },
} as const;

export type ThemeTokens = typeof themeTokens;
