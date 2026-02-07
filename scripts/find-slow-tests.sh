#!/usr/bin/env bash
#
# Recursive parallel test runner to identify slow tests
# Drills down from directories → subdirectories → individual test files → individual tests
#

SLOW_THRESHOLD=${SLOW_THRESHOLD:-5}  # Seconds to consider "slow"
PYTEST_BIN="apps/backend/.venv/bin/pytest"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="test-results/slow-hunt-${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Slow Test Hunter${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "Output directory: ${OUTPUT_DIR}"
echo -e "Slow threshold: ${SLOW_THRESHOLD}s"
echo ""

# Function to run test and capture time - writes elapsed time to stdout
run_and_time() {
    local target="$1"
    local start=$(date +%s.%N)

    timeout 120 "$PYTEST_BIN" "$target" -v --tb=short -m "not slow" -q 2>&1 | tee "${OUTPUT_DIR}/$(basename "$target" | tr '/' '_').log" > /dev/null

    local end=$(date +%s.%N)
    echo "$end - $start" | bc
}

# Function to drill into subdirectories
drill_down() {
    local target_dir="$1"
    local label="$2"
    local depth="${3:-0}"

    if [[ $depth -ge 3 ]]; then
        echo -e "${YELLOW}Max depth reached, skipping further drill-down${NC}"
        return
    fi

    echo ""
    echo -e "${BLUE}=== Drilling down: $label (depth $depth) ===${NC}"

    local subdirs=$(find "$target_dir" -mindepth 1 -maxdepth 1 -type d ! -name "__pycache__" 2>/dev/null)

    if [[ -z "$subdirs" ]]; then
        echo -e "${YELLOW}No subdirectories found, testing individual files...${NC}"

        # Test individual files
        local files=$(find "$target_dir" -maxdepth 1 -name "test_*.py" -type f 2>/dev/null)
        if [[ -n "$files" ]]; then
            local slow_files=()

            while IFS= read -r file; do
                local filename=$(basename "$file")
                echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} Testing file: $filename"

                local elapsed=$(run_and_time "$file")
                elapsed=$(printf "%.2f" "$elapsed")

                if (( $(echo "$elapsed >= $SLOW_THRESHOLD" | bc -l) )); then
                    echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} ${filename} took ${elapsed}s - ${RED}SLOW${NC}"
                    slow_files+=("$filename:$elapsed")
                else
                    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} ${filename} completed in ${elapsed}s"
                fi
            done <<< "$files"

            # If slow files found, drill into individual tests
            for slow_file in "${slow_files[@]}"; do
                local filename="${slow_file%%:*}"
                local elapsed="${slow_file##*:}"
                local filepath="$target_dir/$filename"

                echo ""
                echo -e "${BLUE}=== Drilling into tests in $filename ===${NC}"

                # Get individual tests
                local tests=$("$PYTEST_BIN" "$filepath" --collect-only -q 2>/dev/null | grep "::test_" | sed 's/^[[:space:]]*//')

                if [[ -n "$tests" ]]; then
                    while IFS= read -r test_name; do
                        local test_id="$filepath::${test_name##*::}"
                        local test_name_short="${test_name##*::}"

                        echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} Testing: $test_name_short"

                        local test_elapsed=$(run_and_time "$test_id")
                        test_elapsed=$(printf "%.2f" "$test_elapsed")

                        if (( $(echo "$test_elapsed >= $SLOW_THRESHOLD" | bc -l) )); then
                            echo -e "${RED}SLOW TEST: $test_id - ${test_elapsed}s${NC}"
                            echo "$test_id" >> "${OUTPUT_DIR}/slow_tests.txt"
                        else
                            echo -e "${GREEN}OK: $test_id - ${test_elapsed}s${NC}"
                        fi
                    done <<< "$tests"
                fi
            done
        fi
    else
        # Run subdirectories
        local slow_subdirs=()

        while IFS= read -r subdir; do
            local dirname=$(basename "$subdir")
            echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} Testing subdirectory: $dirname"

            local elapsed=$(run_and_time "$subdir")
            elapsed=$(printf "%.2f" "$elapsed")

            if (( $(echo "$elapsed >= $SLOW_THRESHOLD" | bc -l) )); then
                echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} ${dirname} took ${elapsed}s - ${RED}SLOW${NC}"
                slow_subdirs+=("$subdir:$elapsed")
            else
                echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} ${dirname} completed in ${elapsed}s"
            fi
        done <<< "$subdirs"

        # Recursively drill into slow subdirectories
        for slow_subdir in "${slow_subdirs[@]}"; do
            local subdir_path="${slow_subdir%%:*}"
            local subdir_name=$(basename "$subdir_path")
            drill_down "$subdir_path" "${label}_${subdir_name}" $((depth + 1))
        done
    fi
}

# Main execution - run directories in parallel
echo -e "${BLUE}=== Phase 1: Testing top-level directories in parallel ===${NC}"

slow_top_dirs=()
pids=()
declare -A dir_names

for dir in tests/*/; do
    if [[ -d "$dir" ]]; then
        dirname=$(basename "$dir")
        echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} Testing: $dirname"

        # Run in background with time measurement
        (
            start=$(date +%s.%N)
            timeout 120 "$PYTEST_BIN" "$dir" -v --tb=short -m "not slow" -q > "${OUTPUT_DIR}/${dirname}.log" 2>&1
            exit_code=$?
            end=$(date +%s.%N)
            echo "$end - $start" | bc > "${OUTPUT_DIR}/${dirname}.time"
            echo $exit_code > "${OUTPUT_DIR}/${dirname}.exit"
        ) &

        pids+=($!)
        dir_names[$!]="$dirname"
    fi
done

# Wait for all top-level directories
for pid in "${pids[@]}"; do
    wait $pid 2>/dev/null
    dirname="${dir_names[$pid]}"
    time_file="${OUTPUT_DIR}/${dirname}.time"

    if [[ -f "$time_file" ]]; then
        elapsed=$(cat "$time_file" 2>/dev/null || echo "0")
        elapsed=$(printf "%.2f" "$elapsed")

        if (( $(echo "$elapsed >= $SLOW_THRESHOLD" | bc -l) )); then
            echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} ${dirname} took ${elapsed}s - ${RED}SLOW - investigating...${NC}"
            slow_top_dirs+=("tests/$dirname")
        else
            echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} ${dirname} completed in ${elapsed}s"
        fi
    fi
done

# Drill down into slow directories
for slow_dir in "${slow_top_dirs[@]}"; do
    drill_down "$slow_dir" "$(basename "$slow_dir")"
done

echo ""
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}=====================================${NC}"

if [[ -f "${OUTPUT_DIR}/slow_tests.txt" ]]; then
    echo -e "${RED}Slow tests found:${NC}"
    cat "${OUTPUT_DIR}/slow_tests.txt"
else
    echo -e "${GREEN}No slow tests found!${NC}"
fi

echo ""
echo -e "Results saved to: ${OUTPUT_DIR}"
