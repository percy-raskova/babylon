/**
 * Lightweight structured logger for the frontend.
 *
 * Provides leveled logging (debug/info/warn/error) with structured
 * context and correlation ID propagation. Outputs to the browser
 * console in development; can be extended with an HTTP transport
 * for production log aggregation.
 *
 * Usage:
 *   import { createLogger } from "@/utils/logger";
 *   const log = createLogger("GameStore");
 *   log.info("Game loaded", { sessionId, tick });
 */

type LogLevel = "debug" | "info" | "warn" | "error";

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/** Minimum log level — controlled by import.meta.env.VITE_LOG_LEVEL */
const MIN_LEVEL: LogLevel = ((import.meta.env.VITE_LOG_LEVEL as LogLevel | undefined) ??
  "debug") as LogLevel;

/** Correlation ID for the current browser session (propagated to API). */
let _correlationId: string = crypto.randomUUID();

/** Get the current correlation ID. */
export function getCorrelationId(): string {
  return _correlationId;
}

/** Reset the correlation ID (e.g., on page reload or new game). */
export function resetCorrelationId(): string {
  _correlationId = crypto.randomUUID();
  return _correlationId;
}

interface LogEntry {
  ts: string;
  level: LogLevel;
  source: string;
  msg: string;
  correlationId: string;
  [key: string]: unknown;
}

interface Logger {
  debug: (msg: string, data?: Record<string, unknown>) => void;
  info: (msg: string, data?: Record<string, unknown>) => void;
  warn: (msg: string, data?: Record<string, unknown>) => void;
  error: (msg: string, data?: Record<string, unknown>) => void;
}

function shouldLog(level: LogLevel): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[MIN_LEVEL];
}

function formatEntry(
  level: LogLevel,
  source: string,
  msg: string,
  data?: Record<string, unknown>,
): LogEntry {
  return {
    ts: new Date().toISOString(),
    level,
    source,
    msg,
    correlationId: _correlationId,
    ...data,
  };
}

/**
 * Create a logger scoped to a component or module name.
 *
 * @param source - Name of the component/module (e.g., "GameStore", "HexMap")
 * @returns Logger instance with debug/info/warn/error methods.
 */
export function createLogger(source: string): Logger {
  return {
    debug(msg: string, data?: Record<string, unknown>) {
      if (!shouldLog("debug")) return;
      const entry = formatEntry("debug", source, msg, data);
      console.debug(`[${source}]`, msg, entry);
    },
    info(msg: string, data?: Record<string, unknown>) {
      if (!shouldLog("info")) return;
      const entry = formatEntry("info", source, msg, data);
      console.info(`[${source}]`, msg, entry);
    },
    warn(msg: string, data?: Record<string, unknown>) {
      if (!shouldLog("warn")) return;
      const entry = formatEntry("warn", source, msg, data);
      console.warn(`[${source}]`, msg, entry);
    },
    error(msg: string, data?: Record<string, unknown>) {
      if (!shouldLog("error")) return;
      const entry = formatEntry("error", source, msg, data);
      console.error(`[${source}]`, msg, entry);
    },
  };
}
