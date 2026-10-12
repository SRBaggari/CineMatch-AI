// Runtime 0 means "unknown" in the dataset (the loader never invents a value).
export function formatRuntime(minutes) {
  return minutes > 0 ? `${minutes} min` : 'Runtime —';
}
