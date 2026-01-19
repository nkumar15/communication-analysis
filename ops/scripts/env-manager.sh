#!/bin/bash
set -e

# Usage: ./env-manager.sh <action> <env> [case] [args...]
# Actions: up, down, stop, restart, logs, ps
# Env: dev, demo
# Case: bank, finance, marketing (Required for demo, optional for dev)

ACTION=$1
ENV=$2
CASE=$3

# Shift args to access remaining docker-compose args
shift 2
if [ -n "$CASE" ] && [[ ! "$CASE" =~ ^- ]]; then
    # Case is present and not a flag
    shift 1
else
    # Case might be empty or a flag, reset CASE variable if it was a flag
    if [[ "$CASE" =~ ^- ]]; then
        CASE=""
    fi
fi
ARGS=$@

# --- 1. Determine Project Name ---
if [ "$ENV" == "dev" ]; then
    PROJECT_NAME="saas-dev"
elif [ "$ENV" == "demo" ]; then
    if [ -z "$CASE" ]; then
        echo "❌ Error: Demo environment requires a specific case."
        echo "Usage: make demo-up case=bank"
        exit 1
    fi
    PROJECT_NAME="saas-demo-$CASE"
else
    echo "❌ Usage: $0 <action> <dev|demo> [case] [args...]"
    exit 1
fi

echo "=================================================="
echo "🌍 Environment: $ENV"
echo "📂 Use Case:    ${CASE:-Default}"
echo "🏗️  Project:     $PROJECT_NAME"
echo "🚀 Action:      $ACTION"
echo "=================================================="

# --- 2. Port Conflict Logic (The "Highlander" Rule: There can be only one) ---
if [ "$ACTION" == "up" ] || [ "$ACTION" == "start" ]; then
    # Identify other running saas projects
    
    KNOWN_PROJECTS=("saas-dev" "saas-demo-bank" "saas-demo-finance" "saas-demo-marketing" "saas-demo-task")
    
    for proj in "${KNOWN_PROJECTS[@]}"; do
        if [ "$proj" != "$PROJECT_NAME" ]; then
            # Check if running
            if docker-compose -p "$proj" ps -q | grep -q .; then
                echo "🛑 Stopping conflicting environment: $proj..."
                docker-compose -p "$proj" stop
            fi
        fi
    done
fi

# --- 3. Execute Docker Compose ---

# Standard profiles we always want for 'up'
PROFILES="--profile core --profile apps --profile workers --profile frontend"

case $ACTION in
    up)
        docker-compose -p $PROJECT_NAME $PROFILES up -d $ARGS
        ;;
    down)
        docker-compose -p $PROJECT_NAME down $ARGS
        ;;
    stop)
         docker-compose -p $PROJECT_NAME stop $ARGS
         ;;
    restart)
        docker-compose -p $PROJECT_NAME down
        docker-compose -p $PROJECT_NAME $PROFILES up -d $ARGS
        ;;
    logs)
        docker-compose -p $PROJECT_NAME logs -f $ARGS
        ;;
    ps)
        docker-compose -p $PROJECT_NAME ps
        ;;
    exec)
        docker-compose -p $PROJECT_NAME exec $ARGS
        ;;
    run)
        docker-compose -p $PROJECT_NAME run $ARGS
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        exit 1
        ;;
esac
