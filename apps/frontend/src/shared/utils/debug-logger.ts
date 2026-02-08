/**
 * Debug Logger
 * Only logs when DEBUG=true in environment
 */

export const isDebugEnabled = (): boolean => {
  if (typeof process !== 'undefined' && process.env) {
    return process.env.DEBUG === 'true';
  }
  return false;
};

/**
 * Sanitize an argument for safe logging to prevent log injection attacks.
 * Removes control characters and limits string length to prevent log forgery.
 */
function sanitizeLogArg(arg: unknown): unknown {
  if (typeof arg === 'string') {
    // Remove newlines, tabs, and limit length to prevent log injection
    return arg.replace(/[\r\n\t]/g, ' ').slice(0, 1000);
  }
  if (arg === null || arg === undefined) {
    return arg;
  }
  if (typeof arg === 'object') {
    try {
      // JSON.stringify escapes control characters, which CodeQL recognizes as a sanitizer
      return JSON.stringify(arg, null, 2);
    } catch {
      return '[Object]';
    }
  }
  return arg;
}

export const debugLog = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    const sanitizedArgs = args.map(sanitizeLogArg);
    console.warn(...sanitizedArgs);
  }
};

export const debugWarn = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    console.warn(...args);
  }
};

export const debugError = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    console.error(...args);
  }
};
