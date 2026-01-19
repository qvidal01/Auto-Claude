/**
 * Session Utilities
 *
 * Handles Claude Code session migration between profiles.
 * Sessions are stored in CLAUDE_CONFIG_DIR/projects/{cwd-path-hash}/{session-id}.jsonl
 * and can be copied between profiles to enable session continuity after profile switches.
 */

import { existsSync, mkdirSync, copyFileSync, cpSync, unlinkSync } from 'fs';
import { join, dirname } from 'path';
import { homedir } from 'os';

/**
 * Convert a working directory path to the Claude projects path format.
 * Claude uses a sanitized path format: /Users/foo/bar -> -Users-foo-bar
 */
export function cwdToProjectPath(cwd: string): string {
  // Normalize to forward slashes first (cross-platform: Windows C:\foo\bar -> C:/foo/bar)
  const normalized = cwd.replace(/\\/g, '/');
  // Remove Windows drive letter (C:, D:, etc.) to avoid colons in directory names
  // Then replace path separators with dashes and remove leading slash
  return normalized.replace(/^[a-zA-Z]:/, '').replace(/^\//, '').replace(/\//g, '-');
}

/**
 * Get the full path to a session file for a given profile config directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID
 * @returns Full path to the session .jsonl file
 */
export function getSessionFilePath(configDir: string, cwd: string, sessionId: string): string {
  const expandedConfigDir = configDir.startsWith('~')
    ? configDir.replace(/^~/, homedir())
    : configDir;

  const projectPath = cwdToProjectPath(cwd);
  return join(expandedConfigDir, 'projects', projectPath, `${sessionId}.jsonl`);
}

/**
 * Get the full path to a session's tool-results directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID
 * @returns Full path to the session directory (contains tool-results/)
 */
export function getSessionDirPath(configDir: string, cwd: string, sessionId: string): string {
  const expandedConfigDir = configDir.startsWith('~')
    ? configDir.replace(/^~/, homedir())
    : configDir;

  const projectPath = cwdToProjectPath(cwd);
  return join(expandedConfigDir, 'projects', projectPath, sessionId);
}

/**
 * Result of a session migration operation
 */
export interface SessionMigrationResult {
  success: boolean;
  sessionId: string;
  sourceProfile: string;
  targetProfile: string;
  filesCopied: number;
  error?: string;
}

/**
 * Migrate a Claude Code session from one profile to another.
 *
 * This copies the session .jsonl file and any associated tool-results directory
 * from the source profile's config directory to the target profile's config directory.
 *
 * After migration, the session can be resumed with the target profile's credentials
 * using `claude --resume {sessionId}`.
 *
 * @param sourceConfigDir - Source profile's CLAUDE_CONFIG_DIR
 * @param targetConfigDir - Target profile's CLAUDE_CONFIG_DIR
 * @param cwd - Working directory where the session was created
 * @param sessionId - The session UUID to migrate
 * @returns Migration result with success status and details
 */
export function migrateSession(
  sourceConfigDir: string,
  targetConfigDir: string,
  cwd: string,
  sessionId: string
): SessionMigrationResult {
  const result: SessionMigrationResult = {
    success: false,
    sessionId,
    sourceProfile: sourceConfigDir,
    targetProfile: targetConfigDir,
    filesCopied: 0
  };

  // Get source and target paths (declared outside try block for error cleanup)
  const sourceFile = getSessionFilePath(sourceConfigDir, cwd, sessionId);
  const targetFile = getSessionFilePath(targetConfigDir, cwd, sessionId);
  const sourceDir = getSessionDirPath(sourceConfigDir, cwd, sessionId);
  const targetDir = getSessionDirPath(targetConfigDir, cwd, sessionId);

  try {

    // Check if source session exists
    if (!existsSync(sourceFile)) {
      result.error = `Source session file not found: ${sourceFile}`;
      console.warn('[SessionUtils] Migration failed:', result.error);
      return result;
    }

    // Skip if target already has this session
    if (existsSync(targetFile)) {
      console.warn('[SessionUtils] Session already exists in target profile, skipping copy');
      result.success = true;
      result.filesCopied = 0;
      return result;
    }

    // Ensure target directory exists
    const targetParentDir = dirname(targetFile);
    if (!existsSync(targetParentDir)) {
      mkdirSync(targetParentDir, { recursive: true });
      console.warn('[SessionUtils] Created target directory:', targetParentDir);
    }

    // Copy the session .jsonl file
    copyFileSync(sourceFile, targetFile);
    result.filesCopied++;
    console.warn('[SessionUtils] Copied session file:', sourceFile, '->', targetFile);

    // Copy the session directory (tool-results) if it exists
    if (existsSync(sourceDir)) {
      cpSync(sourceDir, targetDir, { recursive: true });
      result.filesCopied++;
      console.warn('[SessionUtils] Copied session directory:', sourceDir, '->', targetDir);
    }

    result.success = true;
    console.warn('[SessionUtils] Session migration successful:', {
      sessionId,
      filesCopied: result.filesCopied
    });

    return result;
  } catch (error) {
    result.error = error instanceof Error ? error.message : 'Unknown error during migration';
    console.error('[SessionUtils] Migration error:', result.error);

    // Clean up partially migrated session file to enable retry
    // If we copied the .jsonl but failed during tool-results copy,
    // remove the target file so future migrations don't skip it
    if (existsSync(targetFile)) {
      try {
        unlinkSync(targetFile);
        console.warn('[SessionUtils] Cleaned up partial migration file:', targetFile);
      } catch (cleanupError) {
        console.error('[SessionUtils] Failed to cleanup partial migration:',
          cleanupError instanceof Error ? cleanupError.message : 'Unknown cleanup error');
      }
    }

    return result;
  }
}

/**
 * Check if a session exists in a profile's config directory.
 *
 * @param configDir - The profile's CLAUDE_CONFIG_DIR path
 * @param cwd - The working directory where the session was created
 * @param sessionId - The session UUID to check
 * @returns true if the session file exists
 */
export function sessionExists(configDir: string, cwd: string, sessionId: string): boolean {
  const sessionFile = getSessionFilePath(configDir, cwd, sessionId);
  return existsSync(sessionFile);
}
