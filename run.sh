#!/bin/bash

# Configuration
ENV_FILE=".env"
TIMEOUT=15

# Function to prompt with timeout
prompt_with_timeout() {
    local prompt_msg=$1
    local var_name=$2
    local default_val=$3
    local input_val

    echo -n "$prompt_msg"
    read -t $TIMEOUT input_val
    if [ $? -gt 128 ]; then
        echo -e "\nTimeout reached ($TIMEOUT seconds). Exiting."
        exit 1
    fi
    
    if [ -z "$input_val" ]; then
        eval "$var_name=\"$default_val\""
    else
        eval "$var_name=\"$input_val\""
    fi
}

# Function to generate random secret
generate_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        # fallback if openssl not found
        date +%s | sha256sum | base64 | head -c 32
    fi
}

# Check for non-interactive mode
NON_INTERACTIVE=false
if [[ "$1" == "--non-interactive" || "$1" == "-n" ]]; then
    NON_INTERACTIVE=true
fi

# Load existing .env if it exists
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' $ENV_FILE | xargs)
fi

# Ensure AUTH_SECRET exists
if [ -z "$AUTH_SECRET" ]; then
    AUTH_SECRET=$(generate_secret)
    echo "AUTH_SECRET=$AUTH_SECRET" >> $ENV_FILE
    echo "Generated new AUTH_SECRET"
fi

if [ "$NON_INTERACTIVE" = true ]; then
    echo "Running in non-interactive mode..."
    # Check required vars
    MISSING=false
    [ -z "$REDIS_PASSWORD" ] && echo "Missing REDIS_PASSWORD" && MISSING=true
    [ -z "$DEFAULT_ADMIN_USER" ] && echo "Missing DEFAULT_ADMIN_USER" && MISSING=true
    [ -z "$DEFAULT_ADMIN_PASSWORD" ] && echo "Missing DEFAULT_ADMIN_PASSWORD" && MISSING=true
    
    if [ "$MISSING" = true ]; then
        exit 1
    fi
    docker compose up -d --build
else
    echo "--- Voting App Deployment Setup ---"
    
    # REDIS_PASSWORD setup
    if [ -z "$REDIS_PASSWORD" ]; then
        prompt_with_timeout "Enter Redis Password: " REDIS_PASSWORD "password123"
        echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> $ENV_FILE
    fi

    # Admin User setup
    if [ -z "$DEFAULT_ADMIN_USER" ]; then
        prompt_with_timeout "Enter Admin Username [admin]: " DEFAULT_ADMIN_USER "admin"
        echo "DEFAULT_ADMIN_USER=$DEFAULT_ADMIN_USER" >> $ENV_FILE
    fi

    # Admin Password setup
    if [ -z "$DEFAULT_ADMIN_PASSWORD" ]; then
        prompt_with_timeout "Enter Admin Password [admin123]: " DEFAULT_ADMIN_PASSWORD "admin123"
        echo "DEFAULT_ADMIN_PASSWORD=$DEFAULT_ADMIN_PASSWORD" >> $ENV_FILE
    fi

    # Seed data setup
    prompt_with_timeout "Run seed data? [y/N]: " RUN_SEED "n"
    
    if [[ "$RUN_SEED" =~ ^[Yy]$ ]]; then
        echo "Starting services with seed data..."
        docker compose --profile seed up -d --build
    else
        echo "Starting services without seed data..."
        docker compose up -d --build
    fi
fi

echo "Deployment complete."
echo "Access the app at: http://localhost"
