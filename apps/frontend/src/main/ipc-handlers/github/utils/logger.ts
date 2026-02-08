/**
 * Shared debug logging utilities for GitHub handlers
 */

const DEBUG = process.env.DEBUG === 'true' || process.env.NODE_ENV === 'development';

/**
 * Sanitize string data for safe logging
 *
 * Removes control characters (especially newlines and carriage returns)
 * that could be used for log injection attacks.
 */
function sanitizeForLog(data: string, maxLength = 500): string {
  if (!data) return '';

  // Remove control characters that could enable log injection
  // Keep tabs for formatting, remove everything else
  const sanitized = data
    .replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')  // Remove control chars except tab
    .replace(/[\r\n]+/g, '⏎ ')  // Replace newlines with visible symbol
    .substring(0, maxLength);  // Limit length

  return sanitized;
}

/**
 * Create a context-specific logger
 */
export function createContextLogger(context: string): {
  debug: (message: string, data?: unknown) => void;
} {
  return {
    debug: (message: string, data?: unknown): void => {
      if (DEBUG) {
        const safeMessage = sanitizeForLog(message, 1000);
        if (data !== undefined) {
          // If data is a string, sanitize it before logging
          if (typeof data === 'string') {
            console.warn(`[${context}] ${safeMessage}`, sanitizeForLog(data));
          } else {
            console.warn(`[${context}] ${safeMessage}`, data);
          }
        } else {
          console.warn(`[${context}] ${safeMessage}`);
        }
      }
    },
  };
}

/**
 * Log message with context (legacy compatibility)
 */
export function debugLog(context: string, message: string, data?: unknown): void {
  if (DEBUG) {
    const safeMessage = sanitizeForLog(message, 1000);
    if (data !== undefined) {
      // If data is a string, sanitize it before logging
      if (typeof data === 'string') {
        console.warn(`[${context}] ${safeMessage}`, sanitizeForLog(data));
      } else {
        console.warn(`[${context}] ${safeMessage}`, data);
      }
    } else {
      console.warn(`[${context}] ${safeMessage}`);
    }
  }
}
