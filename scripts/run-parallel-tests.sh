#!/bin/bash
# Parallel Test Runner - runs tests per subdirectory to identify slow/hanging tests

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

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Output directory for test results
OUTPUT_DIR="test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="$OUTPUT_DIR/run-$TIMESTAMP"

# Create output directory
mkdir -p "$RUN_DIR"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Parallel Test Runner${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Output directory: $RUN_DIR"
echo ""

# Define test directories to run (leaf directories with actual tests)
# Format: "path|display_name"
TEST_DIRS=(
    "tests/agents|agents"
    "tests/agents/tools_pkg|agents_tools"
    "tests/analysis|analysis"
    "tests/cli|cli"
    "tests/context|context"
    "tests/core|core"
    "tests/core/workspace|core_workspace"
    "tests/ideation|ideation"
    "tests/implementation_plan|implementation_plan"
    "tests/integrations/graphiti|graphiti"
    "tests/integrations/graphiti/providers_pkg|graphiti_providers"
    "tests/integrations/graphiti/providers_pkg/embedder_providers|graphiti_embedder_providers"
    "tests/integrations/graphiti/providers_pkg/llm_providers|graphiti_llm_providers"
    "tests/integrations/graphiti/queries_pkg|graphiti_queries"
    "tests/integrations/linear|linear"
    "tests/memory|memory"
    "tests/merge|merge"
    "tests/merge/ai_resolver|merge_ai_resolver"
    "tests/merge/auto_merger|merge_auto_merger"
    "tests/merge/file_evolution|merge_file_evolution"
    "tests/merge/semantic_analysis|merge_semantic_analysis"
    "tests/phase_config|phase_config"
    "tests/planner_lib|planner_lib"
    "tests/prediction|prediction"
    "tests/project|project"
    "tests/project/command_registry|project_command_registry"
    "tests/prompts_pkg|prompts_pkg"
    "tests/qa|qa"
    "tests/query_memory|query_memory"
    "tests/relative/path|relative_path"
    "tests/review|review"
    "tests/scripts|scripts"
    "tests/security|security"
    "tests/services|services"
    "tests/spec|spec"
    "tests/spec/phases|spec_phases"
    "tests/spec/pipeline|spec_pipeline"
    "tests/spec/validate_pkg|spec_validate_pkg"
    "tests/spec/validate_pkg/validators|spec_validators"
    "tests/task_logger|task_logger"
    "tests/test_core|test_core"
    "tests/test_project|test_project"
    "tests/ui|ui"
)

# Also include root-level test files
ROOT_TESTS=""
for f in tests/test_*.py; do
    if [ -f "$f" ]; then
        ROOT_TESTS="$ROOT_TESTS $f"
    fi
done

# Function to run tests for a directory
run_test_dir() {
    # Disable exit-on-error for this function to handle test failures gracefully
    set +e

    local dir_path="$1"
    local display_name="$2"
    local output_file="$RUN_DIR/${display_name}.log"
    local summary_file="$RUN_DIR/${display_name}-summary.txt"

    # Trap to ensure summary is always written
    trap "echo 'Status: INTERRUPTED' > \"$summary_file\" 2>/dev/null; echo 'Duration: INTERRUPTED' >> \"$summary_file\" 2>/dev/null" EXIT INT TERM

    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} Starting: $display_name ($dir_path)"

    # Record start time
    local start_time=$(date +%s)

    # Run pytest with timeout (600 seconds = 10 minutes per test directory)
    # Use --tb=short for cleaner output
    # Capture both stdout and stderr
    timeout 600 "$PYTEST_BIN" "$dir_path" -v --tb=short --showlocals > "$output_file" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        local status="PASSED"
    elif [ $exit_code -eq 124 ]; then
        local status="TIMEOUT"
    else
        local status="FAILED (exit=$exit_code)"
    fi

    # Record end time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Write summary (always do this, even if earlier commands failed)
    {
        echo "Status: $status"
        echo "Duration: ${duration}s"
        echo "Directory: $dir_path"
        echo "Log file: ${display_name}.log"
    } > "$summary_file" || true

    # Parse results from output
    if grep -q "passed" "$output_file" 2>/dev/null; then
        local passed=$(grep -oP '\d+(?= passed)' "$output_file" 2>/dev/null | tail -1 || echo "0")
        local failed=$(grep -oP '\d+(?= failed)' "$output_file" 2>/dev/null | tail -1 || echo "0")
        local errors=$(grep -oP '\d+(?= error)' "$output_file" 2>/dev/null | tail -1 || echo "0")
        local skipped=$(grep -oP '\d+(?= skipped)' "$output_file" 2>/dev/null | tail -1 || echo "0")
        echo "Results: passed=${passed:-0} failed=${failed:-0} errors=${errors:-0} skipped=${skipped:-0}" >> "$summary_file" || true
    fi

    if [ "$status" = "PASSED" ]; then
        echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} ✓ $display_name completed in ${duration}s"
    else
        echo -e "${RED}[$(date '+%H:%M:%S')]${NC} ✗ $display_name $status in ${duration}s"
    fi

    # Clear the trap
    trap - EXIT INT TERM

    return 0  # Always return success to avoid killing background jobs
}

# Export function and variables for parallel execution
export -f run_test_dir
export OUTPUT_DIR RUN_DIR BLUE GREEN YELLOW RED NC

# Create a tracking file for PIDs
PIDS_FILE="$RUN_DIR/pids.txt"
echo "" > "$PIDS_FILE"

# Start all test directories in parallel
echo "Starting parallel test execution..."
echo ""

JOBS_LIMIT=${TEST_JOBS_LIMIT:-8}  # Default to 8 parallel jobs
ACTIVE_JOBS=0

for test_dir_spec in "${TEST_DIRS[@]}"; do
    IFS='|' read -r dir_path display_name <<< "$test_dir_spec"

    # Skip if directory doesn't exist
    if [ ! -d "$dir_path" ]; then
        echo -e "${YELLOW}Skipping missing directory: $dir_path${NC}"
        continue
    fi

    # Check if there are test files in this directory
    if ! ls "$dir_path"/test_*.py "$dir_path"/*_test.py 2>/dev/null | grep -q .; then
        echo -e "${YELLOW}Skipping empty directory: $dir_path${NC}"
        continue
    fi

    # Wait if we've hit the job limit
    while [ $ACTIVE_JOBS -ge $JOBS_LIMIT ]; do
        sleep 1
        ACTIVE_JOBS=$(jobs -r | wc -l)
    done

    # Run in background (subshell to avoid set -e issues)
    (run_test_dir "$dir_path" "$display_name") &
    echo "$!|$display_name" >> "$PIDS_FILE"
    ACTIVE_JOBS=$(jobs -r | wc -l)
done

# Run root-level tests if any
if [ -n "$ROOT_TESTS" ]; then
    while [ $ACTIVE_JOBS -ge $JOBS_LIMIT ]; do
        sleep 1
        ACTIVE_JOBS=$(jobs -r | wc -l)
    done

    echo -e "${BLUE}Running root-level test files...${NC}"
    (run_test_dir "tests" "root_tests") &
    echo "$!|root_tests" >> "$PIDS_FILE"
fi

# Wait for all background jobs to complete
echo ""
echo "Waiting for all test jobs to complete..."
echo ""

# Wait for all jobs, but continue even if some fail
while true; do
    # Count running background jobs
    RUNNING=$(jobs -r | wc -l)
    if [ "$RUNNING" -eq 0 ]; then
        break
    fi
    sleep 1
done

# Ensure all background jobs are done
wait 2>/dev/null || true

# Generate final summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

SUMMARY_FILE="$RUN_DIR/overall-summary.txt"
{
    echo "Parallel Test Run Summary"
    echo "========================="
    echo "Date: $(date)"
    echo "Output directory: $RUN_DIR"
    echo ""
    echo "Results by directory:"
    echo "---------------------"
} > "$SUMMARY_FILE"

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_TIMEOUT=0
TOTAL_DIRS=0

# Sort by display name and display summary
for summary in "$RUN_DIR"/*-summary.txt; do
    if [ -f "$summary" ]; then
        dir_name=$(basename "$summary" -summary.txt)

        # Skip the overall summary file
        if [ "$dir_name" = "overall" ]; then
            continue
        fi

        status=$(grep "Status:" "$summary" | sed 's/Status: //' | tr -d '\n')
        duration=$(grep "Duration:" "$summary" | sed 's/Duration: //' | tr -d '\n')

        case "$status" in
            PASSED)
                echo -e "${GREEN}✓${NC} $dir_name: ${duration}s"
                TOTAL_PASSED=$((TOTAL_PASSED + 1))
                ;;
            TIMEOUT)
                echo -e "${YELLOW}⏱${NC} $dir_name: ${duration}s (TIMEOUT)"
                TOTAL_TIMEOUT=$((TOTAL_TIMEOUT + 1))
                ;;
            *)
                echo -e "${RED}✗${NC} $dir_name: ${duration}s ($status)"
                TOTAL_FAILED=$((TOTAL_FAILED + 1))
                ;;
        esac

        TOTAL_DIRS=$((TOTAL_DIRS + 1))
    fi
done

echo ""
echo "Summary: $TOTAL_DIRS directories, $TOTAL_PASSED passed, $TOTAL_FAILED failed, $TOTAL_TIMEOUT timeout"
echo ""

# Append to summary file
{
    echo ""
    echo "Overall: $TOTAL_DIRS directories, $TOTAL_PASSED passed, $TOTAL_FAILED failed, $TOTAL_TIMEOUT timeout"
    echo ""
    echo "Failed/Timeout directories:"
    for summary in "$RUN_DIR"/*-summary.txt; do
        if [ -f "$summary" ]; then
            status=$(grep "Status:" "$summary" | cut -d' ' -f2)
            if [ "$status" != "PASSED" ]; then
                dir_name=$(basename "$summary" -summary.txt)
                echo "  - $dir_name: $status"
            fi
        fi
    done
} >> "$SUMMARY_FILE"

cat "$SUMMARY_FILE"

echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "Full results saved to: $RUN_DIR"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "To view individual results:"
echo "  cat $RUN_DIR/<directory>-summary.txt"
echo "  cat $RUN_DIR/<directory>.log"
echo ""
echo "To re-run only failed directories:"
for summary in "$RUN_DIR"/*-summary.txt; do
    if [ -f "$summary" ]; then
        status=$(grep "Status:" "$summary" | cut -d' ' -f2)
        if [ "$status" != "PASSED" ]; then
            dir_name=$(basename "$summary" -summary.txt)
            echo "  pytest $dir_name -v"
        fi
    fi
done

# Exit with error if any tests failed
if [ $TOTAL_FAILED -gt 0 ] || [ $TOTAL_TIMEOUT -gt 0 ]; then
    exit 1
fi
