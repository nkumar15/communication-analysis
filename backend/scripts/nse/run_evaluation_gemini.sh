# Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"

# Run the evaluation
docker exec -e GEMINI_API_KEY="$GEMINI_API_KEY" sso_domain_worker python scripts/nse/evaluate_rag.py > backend/scripts/nse/evaluation_full_log.txt 2>&1
