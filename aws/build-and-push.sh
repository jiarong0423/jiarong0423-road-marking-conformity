#!/bin/sh
# Build and push the gate image. Nothing here reads a credential; it uses
# whatever profile the caller has already configured.
#
#   AWS_REGION=ap-southeast-2 ACCOUNT=123456789012 ./aws/build-and-push.sh v1
set -e
cd "$(dirname "$0")/.."
TAG=${1:?usage: build-and-push.sh <tag>}
: "${AWS_REGION:?set AWS_REGION}"
: "${ACCOUNT:?set ACCOUNT}"
REPO="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/road-marking-gate"

aws ecr describe-repositories --repository-names road-marking-gate \
    --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name road-marking-gate \
       --region "$AWS_REGION" >/dev/null

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
      "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"

# --provenance=false --sbom=false or Lambda refuses the manifest
docker buildx build --platform linux/arm64 \
  --provenance=false --sbom=false \
  -f aws/Dockerfile -t "$REPO:$TAG" --push .

echo "pushed $REPO:$TAG"
