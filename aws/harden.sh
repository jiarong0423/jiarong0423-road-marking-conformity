#!/bin/sh
# Deploy v13 (with the access gate) and harden the function. Run by the owner.
# Safe to re-run: the token file is reused and every step is idempotent.
#
#   ./aws/harden.sh you@example.com
#   MEMORY=3008 ./aws/harden.sh you@example.com   (accounts still capped at 3008 MB)
#
# The argument is where the $5 budget alert is emailed (optional; omit to skip
# the budget). The access token is generated here, written to
# ~/road116_access_token.txt (mode 600) and never printed. Give it to judges with
# the submission; they send it as the x-access-token header on POST.
set -eu
cd "$(dirname "$0")/.."
export AWS_PROFILE="${AWS_PROFILE:-fitstyle}" AWS_REGION="${AWS_REGION:-ap-southeast-2}"
FN=road-marking-gate
EMAIL="${1:-}"
MEMORY="${MEMORY:-10240}"
TOKEN_FILE="$HOME/road116_access_token.txt"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export ACCOUNT

echo "1/7 build and push v13"
./aws/build-and-push.sh v13 >/dev/null
echo "2/7 point the function at v13"
aws lambda update-function-code --function-name $FN \
  --image-uri "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/road-marking-gate:v13" >/dev/null
aws lambda wait function-updated --function-name $FN

echo "3/7 access token and ${MEMORY} MB memory"
if [ ! -s "$TOKEN_FILE" ]; then
  (umask 077; openssl rand -hex 16 > "$TOKEN_FILE")
fi
chmod 600 "$TOKEN_FILE"
aws lambda update-function-configuration --function-name $FN --memory-size "$MEMORY" \
  --environment "Variables={ACCESS_TOKEN=$(cat "$TOKEN_FILE")}" >/dev/null
aws lambda wait function-updated --function-name $FN

echo "4/7 throttle the API: 1 request/s, bursts of 3"
# Reserved concurrency is not possible on this account: its total concurrency is 10
# and AWS keeps 10 unreserved, so the account limit itself already caps it at 10.
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='road-marking-gate'].ApiId | [0]" --output text)
aws apigatewayv2 update-stage --api-id "$API_ID" --stage-name '$default' \
  --default-route-settings ThrottlingRateLimit=1,ThrottlingBurstLimit=3 >/dev/null

echo "5/7 keep logs 14 days"
aws logs put-retention-policy --log-group-name /aws/lambda/$FN --retention-in-days 14

echo "6/7 remove the unused Function URL (it returned 403) and its two public permissions"
aws lambda delete-function-url-config --function-name $FN 2>/dev/null || echo "   no Function URL"
for sid in public-invoke FunctionURLAllowPublicAccess; do
  aws lambda remove-permission --function-name $FN --statement-id $sid 2>/dev/null || echo "   no statement $sid"
done

echo "7/7 budget alert"
if [ -n "$EMAIL" ]; then
  aws budgets create-budget --region us-east-1 --account-id "$ACCOUNT" \
    --budget '{"BudgetName":"road-marking-gate-5usd","BudgetLimit":{"Amount":"5","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
    --notifications-with-subscribers "[{\"Notification\":{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":80,\"ThresholdType\":\"PERCENTAGE\"},\"Subscribers\":[{\"SubscriptionType\":\"EMAIL\",\"Address\":\"$EMAIL\"}]}]" \
    2>/dev/null && echo "   budget created: alert at 80% of \$5" || echo "   budget not created (already exists?)"
else
  echo "   skipped (no email given)"
fi

echo
echo "done:"
aws lambda get-function-configuration --function-name $FN \
  --query '{memory:MemorySize,timeout:Timeout,state:State}' --output text
aws apigatewayv2 get-stage --api-id "$API_ID" --stage-name '$default' \
  --query 'DefaultRouteSettings.{rate:ThrottlingRateLimit,burst:ThrottlingBurstLimit}' --output text
aws lambda get-function --function-name $FN --query 'Code.ImageUri' --output text | sed 's/^[0-9]*\./<account>./'
echo "access token saved in $TOKEN_FILE (not shown)"
