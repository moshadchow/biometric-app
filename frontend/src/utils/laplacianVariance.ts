/**
 * Approximate Laplacian variance for a grayscale pixel grid.
 * Higher value = sharper image.
 * gray[] is row-major, width cols x height rows.
 */
export function laplacianVariance(
  gray: number[],
  width: number,
  height: number
): number {
  let variance = 0;
  let count = 0;
  for (let row = 1; row < height - 1; row++) {
    for (let col = 1; col < width - 1; col++) {
      const i = row * width + col;
      const lap =
        -gray[i - width - 1] -
        gray[i - width] -
        gray[i - width + 1] -
        gray[i - 1] +
        8 * gray[i] -
        gray[i + 1] -
        gray[i + width - 1] -
        gray[i + width] -
        gray[i + width + 1];
      variance += lap * lap;
      count++;
    }
  }
  return count > 0 ? variance / count : 0;
}
