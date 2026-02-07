# Test Scripts

This directory contains utility scripts for running tests in various ways.

## Parallel Test Runners

These scripts help identify slow or hanging tests by running them in parallel per directory or per file.

### `run-parallel-tests.sh` - Directory-level parallel execution

Runs tests for each subdirectory in parallel, outputting results to separate log files.

```bash
# Run all tests in parallel (default 8 concurrent jobs)
./scripts/run-parallel-tests.sh

# Customize number of parallel jobs
TEST_JOBS_LIMIT=16 ./scripts/run-parallel-tests.sh
```

**Output:**
- `test-results/run-YYYYMMDD_HHMMSS/` - Directory containing all results
- `<directory>-summary.txt` - Quick summary for each directory (status, duration)
- `<directory>.log` - Full pytest output for each directory
- `overall-summary.txt` - Combined summary of all results

**Use case:** When you want to identify which test directories have issues.

### `run-tests-per-file.sh` - File-level parallel execution

Runs each test file individually for more granular debugging.

```bash
# Run all test files in parallel
./scripts/run-tests-per-file.sh

# Run only files in a specific directory
./scripts/run-tests-per-file.sh tests/context

# Customize parallel jobs and timeout
TEST_JOBS_LIMIT=20 TEST_TIMEOUT_SECONDS=60 ./scripts/run-tests-per-file.sh
```

**Output:**
- `test-results/run-by-file-YYYYMMDD_HHMMSS/` - Directory containing all results
- `<test_file>-summary.txt` - Quick summary for each file
- `<test_file>.log` - Full pytest output
- `overall-summary.txt` - Combined summary

**Use case:** When you've identified a problematic directory and need to find the specific test file.

## Environment Variables

Both scripts support these environment variables:

- `TEST_JOBS_LIMIT` - Number of parallel jobs (default: 8 for directories, 12 for files)
- `TEST_TIMEOUT_SECONDS` - Timeout before killing a test run (default: 600s for dirs, 120s for files)

## Example Workflow

1. **Find problematic directories:**
   ```bash
   ./scripts/run-parallel-tests.sh
   ```

2. **Drill down into problematic directories:**
   ```bash
   ./scripts/run-tests-per-file.sh tests/integrations/graphiti
   ```

3. **View results:**
   ```bash
   # See overall summary
   cat test-results/run-*/overall-summary.txt

   # See specific directory results
   cat test-results/run-*/graphiti-summary.txt
   cat test-results/run-*/graphiti.log
   ```

4. **Re-run specific tests:**
   ```bash
   # Run individual file
   pytest tests/integrations/graphiti/test_graphiti_memory.py -v

   # Run specific test
   pytest tests/integrations/graphiti/test_graphiti_memory.py::test_specific_function -v
   ```

## Interpreting Results

- **PASSED** - All tests in the directory/file passed
- **FAILED** - Tests failed (check the .log file for details)
- **TIMEOUT** - Tests exceeded the timeout limit (likely hanging)

When tests timeout or fail, check the corresponding `.log` file for:
- Which specific tests failed
- Error messages and stack traces
- Whether tests are waiting on external resources (network, APIs, etc.)
