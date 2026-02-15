/**
 * Extract a concise title from a subtask description.
 *
 * Strategy:
 * 1. Return '' for empty/undefined input (lets i18n fallback activate in UI)
 * 2. If description fits within maxLength, return as-is
 * 3. Try extracting the first sentence (split on '. ' or ': ')
 * 4. If first sentence fits, return it (strip trailing period)
 * 5. Otherwise truncate at last word boundary and append ellipsis
 */
export function extractSubtaskTitle(description: string | undefined | null, maxLength = 80): string {
  if (!description || !description.trim()) {
    return '';
  }

  const trimmed = description.trim();

  if (trimmed.length <= maxLength) {
    return trimmed;
  }

  // Try to extract first sentence via '. ' or ': '
  const sentenceMatch = trimmed.match(/^(.+?(?:\. |: ))/);
  if (sentenceMatch) {
    let sentence = sentenceMatch[1].trimEnd();
    // Strip trailing period or colon+space artifacts
    sentence = sentence.replace(/[.:]\s*$/, '');
    if (sentence.length <= maxLength) {
      return sentence;
    }
  }

  // Truncate at last word boundary within maxLength
  const truncated = trimmed.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  const cutoff = lastSpace > 0 ? lastSpace : maxLength;

  return `${trimmed.substring(0, cutoff)}\u2026`;
}
