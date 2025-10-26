# Setting Up Custom Domain for LA Geography API

**Goal**: Replace the default API Gateway URL with `api.stilesdata.com/la-geography`

**Current URL**: `https://v7cwkba61i.execute-api.us-west-2.amazonaws.com/prod/lookup`  
**New URL**: `https://api.stilesdata.com/la-geography/lookup`

---

## Prerequisites

✅ You own `stilesdata.com` and it's in Route53  
✅ API is deployed and working  
✅ AWS CLI configured with profile `haekeo`

---

## Step 1: Request SSL Certificate (ACM)

**IMPORTANT**: Certificate must be in `us-east-1` for API Gateway custom domains, even though your API is in `us-west-2`.

```bash
# Request certificate for api.stilesdata.com
aws acm request-certificate \
  --domain-name api.stilesdata.com \
  --validation-method DNS \
  --region us-east-1 \
  --profile haekeo
```

**Output** will include a `CertificateArn`. Save it!

```json
{
    "CertificateArn": "arn:aws:acm:us-east-1:399949164916:certificate/xxxxx-xxxxx-xxxxx"
}
```

### Validate the certificate

Get the validation CNAME records:

```bash
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:399949164916:certificate/YOUR-CERT-ID" \
  --region us-east-1 \
  --profile haekeo \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

This gives you a CNAME record to add to Route53:

```json
{
    "Name": "_xxx.api.stilesdata.com.",
    "Type": "CNAME",
    "Value": "_yyy.acm-validations.aws."
}
```

**Add this CNAME to Route53**:

```bash
# Get your hosted zone ID for stilesdata.com
aws route53 list-hosted-zones \
  --profile haekeo \
  --query 'HostedZones[?Name==`stilesdata.com.`].[Id,Name]' \
  --output table

# The validation can take 5-30 minutes
# Check status:
aws acm describe-certificate \
  --certificate-arn "arn:aws:acm:us-east-1:399949164916:certificate/YOUR-CERT-ID" \
  --region us-east-1 \
  --profile haekeo \
  --query 'Certificate.Status'
```

Wait for status to be `ISSUED` before proceeding.

---

## Step 2: Create Custom Domain in API Gateway

```bash
# Create custom domain name (in us-west-2 where your API is)
aws apigatewayv2 create-domain-name \
  --domain-name api.stilesdata.com \
  --domain-name-configurations CertificateArn="arn:aws:acm:us-east-1:399949164916:certificate/YOUR-CERT-ID" \
  --region us-west-2 \
  --profile haekeo
```

**Output** includes `DomainNameConfigurations` with a `ApiGatewayDomainName`. Save this - you'll need it for DNS!

```json
{
    "DomainNameConfigurations": [
        {
            "ApiGatewayDomainName": "d-xxxxxxxxx.execute-api.us-west-2.amazonaws.com",
            ...
        }
    ]
}
```

---

## Step 3: Create API Mapping

Map `api.stilesdata.com/la-geography` to your API:

```bash
# Get your API ID (should be v7cwkba61i)
aws apigatewayv2 get-apis \
  --region us-west-2 \
  --profile haekeo \
  --query 'Items[?Name==`la-geography-lookup-api`].[ApiId,Name]'

# Create the mapping
aws apigatewayv2 create-api-mapping \
  --domain-name api.stilesdata.com \
  --api-id v7cwkba61i \
  --stage prod \
  --api-mapping-key la-geography \
  --region us-west-2 \
  --profile haekeo
```

This maps:
- `api.stilesdata.com/la-geography/*` → your API at stage `prod`

---

## Step 4: Update Route53 DNS

Create an A record (Alias) pointing to the API Gateway domain:

```bash
# Get your hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --profile haekeo \
  --query 'HostedZones[?Name==`stilesdata.com.`].Id' \
  --output text | sed 's/\/hostedzone\///')

echo "Hosted Zone ID: $HOSTED_ZONE_ID"

# Create change batch file
cat > /tmp/route53-change.json << 'EOF'
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.stilesdata.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2OJLYMUO9EFXC",
          "DNSName": "REPLACE-WITH-API-GATEWAY-DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

# Replace the DNSName with your API Gateway domain from Step 2
# Then apply:
aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/route53-change.json \
  --profile haekeo
```

**Note**: The `HostedZoneId` `Z2OJLYMUO9EFXC` is the fixed zone ID for API Gateway in us-west-2 (not your Route53 zone).

---

## Step 5: Test!

Wait 2-5 minutes for DNS propagation, then test:

```bash
# Test the new custom domain
curl "https://api.stilesdata.com/la-geography/lookup?lat=34.0522&lon=-118.2437"

# Should return the same result as the old URL
```

---

## Verification Checklist

✅ Certificate status is `ISSUED` in ACM  
✅ Custom domain created in API Gateway  
✅ API mapping exists for path `la-geography`  
✅ Route53 A record (Alias) points to API Gateway  
✅ DNS resolves correctly: `dig api.stilesdata.com`  
✅ HTTPS works: `curl https://api.stilesdata.com/la-geography/lookup?lat=34.0522&lon=-118.2437`

---

## Troubleshooting

### Certificate validation stuck

- Check Route53 has the CNAME record
- Wait up to 30 minutes
- Verify domain ownership

### DNS not resolving

- Wait 5-10 minutes for DNS propagation
- Check with: `dig api.stilesdata.com`
- Verify A record exists in Route53

### 403 Forbidden

- Check API mapping path matches: `/la-geography/*`
- Verify API stage is `prod`
- Check custom domain is in same region as API (us-west-2)

### Certificate error

- Ensure certificate is in `us-east-1`
- Verify certificate domain matches exactly: `api.stilesdata.com`
- Check certificate status is `ISSUED`

---

## Cost

- **ACM Certificate**: FREE
- **Custom Domain**: FREE
- **Route53 hosted zone**: ~$0.50/month (existing)
- **Route53 queries**: $0.40 per million queries

No additional cost beyond what you're already paying!

---

## After Setup

Update documentation:

1. Update `docs/API.md` with new endpoint
2. Update `README.md` 
3. Update `API_DEPLOYED.md`
4. Test all examples with new URL

---

## Alternative: AWS Console Method

If you prefer clicking instead of CLI:

1. **ACM (us-east-1)**:
   - Request certificate for `api.stilesdata.com`
   - Add validation CNAME to Route53
   - Wait for ISSUED status

2. **API Gateway (us-west-2)**:
   - Custom domain names → Create
   - Domain: `api.stilesdata.com`
   - Select certificate
   - Endpoint: Regional
   - Create

3. **API Mappings**:
   - Select your custom domain
   - API mappings → Configure API mappings
   - Add mapping:
     - Path: `la-geography`
     - API: `la-geography-lookup-api`
     - Stage: `prod`

4. **Route53**:
   - Select `stilesdata.com` hosted zone
   - Create record
   - Type: A
   - Record name: `api`
   - Alias: Yes
   - Alias to: API Gateway → us-west-2 → `api.stilesdata.com`

---

## Next Steps

After custom domain is working:

1. Keep old URL working (don't delete) for transition period
2. Update all documentation
3. Notify users of new endpoint
4. Eventually can delete old API Gateway if desired


