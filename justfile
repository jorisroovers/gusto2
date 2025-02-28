# Load environment variables from .env file
set dotenv-load

deploy:
    ssh $PROD_HOST "cd $PROD_GIT_DIR && /usr/local/bin/git pull"
    ssh $PROD_HOST "sudo /usr/local/bin/docker-compose -f $PROD_GIT_DIR/gusto2-app/docker-compose.yml down"
    ssh $PROD_HOST "sudo /usr/local/bin/docker-compose -f $PROD_GIT_DIR/gusto2-app/docker-compose.yml up -d --build"