#!/usr/bin/env node
/**
 * Cross-platform backend test runner script
 * Runs pytest using the correct virtual environment path for Windows/Mac/Linux
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const isWindows = os.platform() === 'win32';
const rootDir = path.join(__dirname, '..');
const backendDir = path.join(rootDir, 'apps', 'backend');
const testsDir = path.join(rootDir, 'tests');
const venvDir = path.join(backendDir, '.venv');

// Get pytest path based on platform
const pytestPath = isWindows
  ? path.join(venvDir, 'Scripts', 'pytest.exe')
  : path.join(venvDir, 'bin', 'pytest');

// Check if venv exists
if (!fs.existsSync(venvDir)) {
  console.error('Error: Virtual environment not found.');
  console.error('Run "npm run install:backend" first.');
  process.exit(1);
}

// Check if pytest is installed
if (!fs.existsSync(pytestPath)) {
  console.error('Error: pytest not found in virtual environment.');
  console.error('Install test dependencies:');
  const pipPath = isWindows
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip');
  console.error(`  "${pipPath}" install -r tests/requirements-test.txt`);
  process.exit(1);
}

// Get any additional args passed to the script
const args = process.argv.slice(2);

// Escape each argument for safe shell usage
function escapeShellArg(arg) {
  // On Windows, escape backslashes and double quotes and wrap in double quotes
  if (isWindows) {
    return `"${arg.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
  }
  // On Unix, use single quotes and escape any single quotes in the argument
  return `'${arg.replace(/'/g, "'\\''")}'`;
}

// Build command with properly escaped arguments
const defaultArgs = ['-v'];
const argsToUse = args.length > 0 ? args : defaultArgs;
const escapedArgs = argsToUse.map(escapeShellArg).join(' ');

// Run pytest with properly escaped paths and arguments
const cmd = isWindows
  ? `"${pytestPath}" "${testsDir}" ${escapedArgs}`
  : `'${pytestPath}' '${testsDir}' ${escapedArgs}`;

console.log(`> ${cmd}\n`);

try {
  execSync(cmd, { stdio: 'inherit', cwd: rootDir });
} catch (error) {
  process.exit(error.status || 1);
}
