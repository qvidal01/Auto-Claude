#!/bin/bash
# Fine-grained Parallel Test Runner - runs tests per FILE to identify specific hanging tests
# Use this when a directory has issues to drill down to the exact test file

set -e

# Use the backend virtual environment Python
PYTHON_BIN="apps/backend/.venv/bin/python"
PYTEST_BIN="apps/backend/.venv/bin/pytest"

# Verify the venv exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Python virtual environment not found at $PYTHON_BIN"
    echo "Please create it first: cd apps/backend && uv venv && uv pip install -r requirements.txt"
    exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OUTPUT_DIR="test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="$OUTPUT_DIR/run-by-file-$TIMESTAMP"

mkdir -p "$RUN_DIR"

JOBS_LIMIT=${TEST_JOBS_LIMIT:-12}
TIMEOUT_SECONDS=${TEST_TIMEOUT_SECONDS:-120}

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Per-File Parallel Test Runner${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Output directory: $RUN_DIR"
echo "Jobs limit: $JOBS_LIMIT"
echo "Timeout per file: ${TIMEOUT_SECONDS}s"
echo ""

# Function to run a single test file
run_test_file() {
    # Disable exit-on-error for this function to handle test failures gracefully
    set +e

    local test_file="$1"
    local base_name=$(basename "$test_file" .py)
    local output_file="$RUN_DIR/${base_name}.log"
    local summary_file="$RUN_DIR/${base_name}-summary.txt"

    # Trap to ensure summary is always written
    trap "echo 'Status: INTERRUPTED' > \"$summary_file\" 2>/dev/null; echo 'Duration: INTERRUPTED' >> \"$summary_file\" 2>/dev/null" EXIT INT TERM

    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} Starting: $base_name"

    local start_time=$(date +%s)

    timeout $TIMEOUT_SECONDS "$PYTEST_BIN" "$test_file" -v --tb=short > "$output_file" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        local status="PASSED"
    elif [ $exit_code -eq 124 ]; then
        local status="TIMEOUT"
    else
        local status="FAILED (exit=$exit_code)"
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    {
        echo "Status: $status"
        echo "Duration: ${duration}s"
        echo "File: $test_file"
        echo "Log file: ${base_name}.log"
    } > "$summary_file" || true

    if [ "$status" = "PASSED" ]; then
        echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} ✓ $base_name (${duration}s)"
    else
        echo -e "${RED}[$(date '+%H:%M:%S')]${NC} ✗ $base_name $status (${duration}s)"
    fi

    # Clear the trap
    trap - EXIT INT TERM

    return 0  # Always return success to avoid killing background jobs
}

export -f run_test_file
export OUTPUT_DIR RUN_DIR BLUE GREEN RED YELLOW NC TIMEOUT_SECONDS

# If a directory is specified, only run tests from that directory
if [ -n "$1" ]; then
    TARGET_DIR="$1"
    echo "Scanning directory: $TARGET_DIR"
    TEST_FILES=$(find "$TARGET_DIR" -maxdepth 1 -type f -name "test_*.py" -o -name "*_test.py" | sort)
else
    echo "Scanning all test directories..."
    TEST_FILES=$(find tests -type f -name "test_*.py" -o -name "*_test.py" | sort)
fi

TOTAL_FILES=$(echo "$TEST_FILES" | wc -l)
echo "Found $TOTAL_FILES test files"
echo ""

ACTIVE_JOBS=0
RUN_COUNT=0

for test_file in $TEST_FILES; do
    [ ! -f "$test_file" ] && continue

    # Wait if we've hit the job limit
    while [ $ACTIVE_JOBS -ge $JOBS_LIMIT ]; do
        sleep 0.5
        ACTIVE_JOBS=$(jobs -r | wc -l)
    done

    (run_test_file "$test_file") &
    ACTIVE_JOBS=$(jobs -r | wc -l)
    RUN_COUNT=$((RUN_COUNT + 1))

    # Progress indicator
    if [ $((RUN_COUNT % 10)) -eq 0 ]; then
        echo -e "${BLUE}Progress: $RUN_COUNT/$TOTAL_FILES files started${NC}"
    fi
done

echo ""
echo "Waiting for all test jobs to complete..."
echo ""

# Wait for all jobs, but continue even if some fail
while true; do
    RUNNING=$(jobs -r | wc -l)
    if [ "$RUNNING" -eq 0 ]; then
        break
    fi
    sleep 1
done

# Ensure all background jobs are done
wait 2>/dev/null || true

# Generate summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Per-File Test Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

SUMMARY_FILE="$RUN_DIR/overall-summary.txt"
{
    echo "Per-File Test Run Summary"
    echo "========================="
    echo "Date: $(date)"
    echo "Total files: $TOTAL_FILES"
    echo ""
} > "$SUMMARY_FILE"

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_TIMEOUT=0

for summary in "$RUN_DIR"/*-summary.txt; do
    if [ -f "$summary" ]; then
        file_name=$(basename "$summary" -summary.txt)
        status=$(grep "Status:" "$summary" | cut -d' ' -f2)
        duration=$(grep "Duration:" "$summary" | cut -d' ' -f2)

        case "$status" in
            PASSED)
                TOTAL_PASSED=$((TOTAL_PASSED + 1))
                ;;
            TIMEOUT)
                echo -e "${YELLOW}⏱${NC} $file_name: ${duration}s (TIMEOUT)"
                TOTAL_TIMEOUT=$((TOTAL_TIMEOUT + 1))
                ;;
            *)
                echo -e "${RED}✗${NC} $file_name: ${duration}s (FAILED)"
                TOTAL_FAILED=$((TOTAL_FAILED + 1))
                ;;
        esac
    fi
done | head -50  # Show first 50 failures

echo ""
echo "Summary: $TOTAL_FILES files, $TOTAL_PASSED passed, $TOTAL_FAILED failed, $TOTAL_TIMEOUT timeout"
echo ""

{
    echo "Overall: $TOTAL_PASSED passed, $TOTAL_FAILED failed, $TOTAL_TIMEOUT timeout"
    echo ""
    echo "Failed/Timeout files:"
    for summary in "$RUN_DIR"/*-summary.txt; do
        if [ -f "$summary" ]; then
            status=$(grep "Status:" "$summary" | cut -d' ' -f2)
            if [ "$status" != "PASSED" ]; then
                file_name=$(basename "$summary" -summary.txt)
                duration=$(grep "Duration:" "$summary" | cut -d' ' -f2)
                echo "  - $file_name: $status (${duration}s)"
            fi
        fi
    done
} >> "$SUMMARY_FILE"

cat "$SUMMARY_FILE"

echo ""
echo -e "${BLUE}=====================================${NC}"
echo "Results saved to: $RUN_DIR"
echo -e "${BLUE}=====================================${NC}"

if [ $TOTAL_FAILED -gt 0 ] || [ $TOTAL_TIMEOUT -gt 0 ]; then
    exit 1
fi
