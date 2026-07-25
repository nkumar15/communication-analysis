#!/bin/bash
# Helper script to quickly start Playwright codegen for recording manual tests

set -e

echo "🎬 Playwright Test Recorder"
echo "=========================="
echo ""

# Check if playwright is installed
if ! python -m playwright --version &> /dev/null; then
    echo "❌ Playwright not found. Installing..."
    pip install playwright
    python -m playwright install chromium
fi

# Get recording name
read -p "Enter test name (e.g., 'create_team'): " TEST_NAME
TEST_NAME="${TEST_NAME// /_}"  # Replace spaces with underscores
DATE=$(date +%Y%m%d)
OUTPUT_FILE="recordings/${TEST_NAME}_${DATE}.py"

# Get starting URL
echo ""
echo "Select starting page:"
echo "1) Login page (http://localhost:3000/login)"
echo "2) Dashboard (http://localhost:3000/dashboard)"  
echo "3) Custom URL"
read -p "Choice [1-3]: " URL_CHOICE

case $URL_CHOICE in
    1)
        START_URL="http://localhost:3000/login"
        ;;
    2)
        START_URL="http://localhost:3000/dashboard"
        ;;
    3)
        read -p "Enter URL: " START_URL
        ;;
    *)
        START_URL="http://localhost:3000/login"
        ;;
esac

echo ""
echo "📹 Starting recorder..."
echo "   URL: $START_URL"
echo "   Output will be saved to: frontend/tests/e2e_browser/$OUTPUT_FILE"
echo ""
echo "👉 Tips:"
echo "   - Perform your actions in the browser"
echo "   - Code will be generated in the Playwright Inspector"
echo "   - Close the browser when done"
echo ""
read -p "Press Enter to start recording..."

# Create recordings directory if it doesn't exist
mkdir -p "recordings"

# Start codegen
python -m playwright codegen \
    --target python-async \
    --output "$OUTPUT_FILE" \
    "$START_URL"

echo ""
echo "✅ Recording saved to: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "1. Review the generated code in $OUTPUT_FILE"
echo "2. Document what you tested in ${TEST_NAME}_${DATE}.md"
echo "3. Share with AI to convert to proper test cases"
echo ""
echo "Quick documentation template created at: recordings/${TEST_NAME}_${DATE}.md"

# Create documentation template
cat > "recordings/${TEST_NAME}_${DATE}.md" << EOF
# Test Recording: ${TEST_NAME}

**Recorded:** $(date +%Y-%m-%d)
**Recorded by:** [Your Name]
**Video:** ${TEST_NAME}_${DATE}.mp4 (if applicable)

## Feature Tested

[Describe what feature or user flow you tested]

## Preconditions

- User: [email]
- Tenant: [tenant name]
- Other setup: [any special setup needed]

## Test Steps

### 1. [First Step]
- **Action:** [what you clicked/typed]
- **Expected:** [what should happen]
- **Selector:** [if known]

### 2. [Second Step]
- **Action:** 
- **Expected:** 
- **Selector:** 

[Add more steps...]

## Actual Results

✅ [What worked]
❌ [Any issues found]

## Screenshots

<!-- Add if available -->
- screenshot_01_description.png
- screenshot_02_description.png

## Notes

[Any additional context, edge cases to handle, etc.]
EOF

echo "Documentation template ready for editing!"
