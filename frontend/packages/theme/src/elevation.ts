/** Border-based depth — cross-platform consistent */
export const elevation = {
  flat: { borderWidth: 1 },
  raised: { borderWidth: 1 },
  overlay: { borderWidth: 1 },
} as const;

export type Elevation = typeof elevation;
