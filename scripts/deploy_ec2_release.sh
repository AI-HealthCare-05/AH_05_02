#!/usr/bin/env bash
# Build, push, and release immutable application images to an EC2 host.
# Secrets never belong in this script, command line, Git, or CI logs.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${DOCKER_USER:?Set DOCKER_USER to the Docker registry account name.}"
: "${DOCKER_REPOSITORY:?Set DOCKER_REPOSITORY to the Docker repository name.}"
: "${APP_VERSION:?Set APP_VERSION, for example v1.0.0.}"
: "${AI_WORKER_VERSION:?Set AI_WORKER_VERSION, usually the same release version.}"
: "${EC2_HOST:?Set EC2_HOST to the EC2 public IP or DNS name.}"
: "${SSH_KEY:?Set SSH_KEY to the path of the EC2 SSH private key.}"

EC2_USER="${EC2_USER:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-~/project}"
APP_IMAGE="${DOCKER_USER}/${DOCKER_REPOSITORY}:app-${APP_VERSION}"
WORKER_IMAGE="${DOCKER_USER}/${DOCKER_REPOSITORY}:ai-${AI_WORKER_VERSION}"

echo "Building immutable release images: ${APP_IMAGE}, ${WORKER_IMAGE}"
docker build --platform linux/amd64 -t "$APP_IMAGE" -f app/Dockerfile .
docker build --platform linux/amd64 -t "$WORKER_IMAGE" -f ai_worker/Dockerfile .

# Authenticate beforehand with `docker login`. This intentionally does not accept
# a password or token argument, preventing credentials from appearing in history.
docker push "$APP_IMAGE"
docker push "$WORKER_IMAGE"

echo "Copying only versioned infrastructure files; EC2 .env and model artifacts remain on the host."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_DIR/infra/docker $REMOTE_DIR/infra/nginx"
scp -i "$SSH_KEY" infra/docker/docker-compose.ec2.yml \
  "$EC2_USER@$EC2_HOST:$REMOTE_DIR/infra/docker/"
scp -i "$SSH_KEY" infra/nginx/ec2-http.conf.template \
  "$EC2_USER@$EC2_HOST:$REMOTE_DIR/infra/nginx/"

ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" \
  "DOCKER_USER='$DOCKER_USER' DOCKER_REPOSITORY='$DOCKER_REPOSITORY' APP_VERSION='$APP_VERSION' AI_WORKER_VERSION='$AI_WORKER_VERSION' bash -s" <<'REMOTE'
set -euo pipefail
cd ~/project
test -f .env || { echo 'Missing ~/project/.env on EC2.' >&2; exit 1; }
docker compose --env-file .env -f infra/docker/docker-compose.ec2.yml pull
docker compose --env-file .env -f infra/docker/docker-compose.ec2.yml up -d --remove-orphans
docker compose --env-file .env -f infra/docker/docker-compose.ec2.yml ps
curl --fail --retry 10 --retry-delay 3 http://127.0.0.1/api/health
REMOTE

echo "Release completed: ${APP_VERSION}"
