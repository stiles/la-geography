#!/bin/bash
set -e

# Setup custom domain for LA Geography API
# Usage: ./setup_custom_domain.sh

DOMAIN="api.stilesdata.com"
BASE_DOMAIN="stilesdata.com"
API_ID="v7cwkba61i"
STAGE="prod"
PATH_KEY="la-geography"
REGION="us-west-2"
CERT_REGION="us-east-1"
PROFILE="haekeo"

echo "🌐 Setting up custom domain: $DOMAIN"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check for existing certificate or request new one
echo "📜 Step 1: SSL Certificate"
echo ""
echo "Checking for existing certificates in $CERT_REGION..."
echo ""

aws acm list-certificates \
  --region "$CERT_REGION" \
  --profile "$PROFILE" \
  --query 'CertificateSummaryList[*].[DomainName,CertificateArn]' \
  --output table

echo ""
read -p "Do you want to use an existing certificate? (y/n): " USE_EXISTING

if [ "$USE_EXISTING" == "y" ] || [ "$USE_EXISTING" == "Y" ]; then
    echo ""
    read -p "Enter the Certificate ARN: " CERT_ARN
    echo -e "${GREEN}✓ Using existing certificate${NC}"
    echo "  ARN: $CERT_ARN"
    echo ""
    
    # Skip validation steps
    SKIP_VALIDATION=true
else
    echo ""
    echo "Requesting new certificate for $DOMAIN..."
    CERT_ARN=$(aws acm request-certificate \
      --domain-name "$DOMAIN" \
      --validation-method DNS \
      --region "$CERT_REGION" \
      --profile "$PROFILE" \
      --query 'CertificateArn' \
      --output text)

    if [ -z "$CERT_ARN" ]; then
        echo -e "${RED}❌ Failed to request certificate${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Certificate requested${NC}"
    echo "  ARN: $CERT_ARN"
    echo ""
    SKIP_VALIDATION=false
fi

# Step 2: Get validation records (skip if using existing cert)
if [ "$SKIP_VALIDATION" == "true" ]; then
    echo "⏭️  Step 2: Skipping validation (using existing certificate)"
    echo ""
else
    echo "⏳ Step 2: Getting DNS validation records..."
    sleep 5  # Wait a moment for AWS to generate validation records

VALIDATION_INFO=$(aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region "$CERT_REGION" \
  --profile "$PROFILE" \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
  --output json)

VALIDATION_NAME=$(echo "$VALIDATION_INFO" | jq -r '.Name')
VALIDATION_VALUE=$(echo "$VALIDATION_INFO" | jq -r '.Value')

echo -e "${YELLOW}⚠️  ACTION REQUIRED: Add this CNAME record to Route53${NC}"
echo ""
echo "  Record Name:  $VALIDATION_NAME"
echo "  Record Type:  CNAME"
echo "  Record Value: $VALIDATION_VALUE"
echo ""
echo "You can add this via AWS Console → Route53 → $BASE_DOMAIN → Create Record"
echo ""
    read -p "Press ENTER once you've added the validation CNAME record..."

    # Step 3: Wait for certificate validation
    echo ""
    echo "⏳ Step 3: Waiting for certificate validation..."
    echo "   (This can take 5-30 minutes)"
    echo ""

    while true; do
        STATUS=$(aws acm describe-certificate \
          --certificate-arn "$CERT_ARN" \
          --region "$CERT_REGION" \
          --profile "$PROFILE" \
          --query 'Certificate.Status' \
          --output text)
        
        if [ "$STATUS" == "ISSUED" ]; then
            echo -e "${GREEN}✓ Certificate validated and issued!${NC}"
            break
        elif [ "$STATUS" == "FAILED" ]; then
            echo -e "${RED}❌ Certificate validation failed${NC}"
            exit 1
        else
            echo "  Status: $STATUS (checking again in 30 seconds...)"
            sleep 30
        fi
    done

    echo ""
fi

# Step 4: Create custom domain (REST API v1)
echo "🌐 Step 4: Creating custom domain in API Gateway..."

DOMAIN_CONFIG=$(aws apigateway create-domain-name \
  --domain-name "$DOMAIN" \
  --regional-certificate-arn "$CERT_ARN" \
  --endpoint-configuration "types=REGIONAL" \
  --region "$REGION" \
  --profile "$PROFILE" \
  2>&1)

if echo "$DOMAIN_CONFIG" | grep -q "ConflictException\|TooManyRequestsException"; then
    echo -e "${YELLOW}⚠️  Domain already exists, continuing...${NC}"
    DOMAIN_CONFIG=$(aws apigateway get-domain-name \
      --domain-name "$DOMAIN" \
      --region "$REGION" \
      --profile "$PROFILE")
fi

API_GATEWAY_DOMAIN=$(echo "$DOMAIN_CONFIG" | jq -r '.regionalDomainName')

echo -e "${GREEN}✓ Custom domain created${NC}"
echo "  API Gateway Domain: $API_GATEWAY_DOMAIN"
echo ""

# Step 5: Create base path mapping (REST API v1)
echo "🔗 Step 5: Creating base path mapping..."

aws apigateway create-base-path-mapping \
  --domain-name "$DOMAIN" \
  --rest-api-id "$API_ID" \
  --stage "$STAGE" \
  --base-path "$PATH_KEY" \
  --region "$REGION" \
  --profile "$PROFILE" \
  2>&1 || echo "Mapping may already exist, continuing..."

echo -e "${GREEN}✓ Base path mapping created${NC}"
echo "  Path: /$PATH_KEY/* → API $API_ID (stage: $STAGE)"
echo ""

# Step 6: Get Route53 hosted zone
echo "📍 Step 6: Setting up DNS in Route53..."

HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --profile "$PROFILE" \
  --query "HostedZones[?Name=='${BASE_DOMAIN}.'].Id" \
  --output text | sed 's/\/hostedzone\///')

if [ -z "$HOSTED_ZONE_ID" ]; then
    echo -e "${RED}❌ Could not find hosted zone for $BASE_DOMAIN${NC}"
    exit 1
fi

echo "  Hosted Zone ID: $HOSTED_ZONE_ID"

# Fixed API Gateway hosted zone for REST APIs in us-west-2 (Regional)
API_GATEWAY_ZONE_ID="Z2OJLYMUO9EFXC"

# Create change batch
cat > /tmp/route53-change-$$.json << EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DOMAIN",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$API_GATEWAY_ZONE_ID",
          "DNSName": "$API_GATEWAY_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch "file:///tmp/route53-change-$$.json" \
  --profile "$PROFILE" \
  > /dev/null

rm /tmp/route53-change-$$.json

echo -e "${GREEN}✓ DNS record created${NC}"
echo ""

# Done!
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Custom domain setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Your API is now available at:"
echo -e "${GREEN}https://$DOMAIN/$PATH_KEY/lookup${NC}"
echo ""
echo "⏳ DNS propagation may take 2-5 minutes. Test with:"
echo ""
echo "  curl \"https://$DOMAIN/$PATH_KEY/lookup?lat=34.0522&lon=-118.2437\""
echo ""
echo "Certificate ARN (save this): $CERT_ARN"
echo ""

