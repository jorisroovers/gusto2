# Load environment variables from .env file
set dotenv-load

deploy:
    ssh $PROD_HOST "cd $PROD_GIT_DIR && /usr/local/bin/git pull"
    # -O option required to use legacy protocol against synology
    scp -O -r "gusto2-app/data" "$PROD_HOST:$PROD_GIT_DIR/gusto2-app/"
    ssh $PROD_HOST "sudo /usr/local/bin/docker-compose -f $PROD_GIT_DIR/gusto2-app/docker-compose.prod.yml down || true"
    ssh $PROD_HOST "sudo /usr/local/bin/docker-compose -f $PROD_GIT_DIR/gusto2-app/docker-compose.prod.yml up -d --build"

# Task to start the entire application with frontend hot reloading (development)
dev:
    cd gusto2-app && docker-compose up --build

# Task to start the application in production mode
prod:
    cd gusto2-app && docker-compose -f docker-compose.prod.yml up --build

# Task to start the application in production mode with detached mode
prod-detached:
    cd gusto2-app && docker-compose -f docker-compose.prod.yml up -d --build