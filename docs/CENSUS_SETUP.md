# Census API key setup

Quick guide to obtaining and configuring your Census API key for demographic data enrichment.

## Get your free API key

1. **Visit the Census API key signup page:**
   https://api.census.gov/data/key_signup.html

2. **Fill out the form:**
   - Organization: Your name or organization
   - Email: Your email address
   - Check "I am not a robot"

3. **Check your email:**
   - You'll receive an email with your API key within a few minutes
   - The key is a long string like: `abc123def456ghi789jkl012mno345pqr678stu901`

## Configure your API key

Choose one of these three methods:

### Method 1: Environment variable (recommended for local development)

```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
export CENSUS_API_KEY="your-key-here"

# Or set for current session only
export CENSUS_API_KEY="your-key-here"
```

### Method 2: Local file (simple, local only)

```bash
# Create a file in the project root
echo "your-key-here" > .census_api_key

# This file is gitignored, so it won't be committed
```

### Method 3: Command line argument

```bash
# Pass key directly when running script
python scripts/fetch_census.py --api-key your-key-here
```

## Verify your setup

Test that your key is working:

```bash
# This will attempt to fetch Census data
make fetch-census
```

If successful, you should see:
```
✓ Census API key loaded (ending in ...xyz)
Fetching Census 2020 block geometries...
```

## Troubleshooting

### "Census API key not found"

- Check that you've set the environment variable or created the `.census_api_key` file
- If using a file, make sure it's in the project root directory
- If using environment variable, restart your terminal or run `source ~/.zshrc`

### "Census API error: Invalid key"

- Double-check that you copied the key correctly
- Make sure there are no extra spaces or quotes
- Verify the key is activated (check your email)

### "Census API error: 403 Forbidden"

- Your key may not be activated yet (can take a few hours)
- Check your email for activation link
- Try again in a few hours

### Rate limits

The Census API has rate limits:
- **500 calls per IP per day** (unauthenticated)
- **Higher limits with API key** (usually sufficient)

If you hit rate limits, wait 24 hours or contact Census for increased limits.

## Security notes

- **Never commit your API key** to version control
- The `.census_api_key` file is gitignored by default
- Be careful not to expose the key in logs or screenshots
- If your key is compromised, request a new one from the Census

## API documentation

For more information about the Census API:
- API home: https://www.census.gov/data/developers.html
- 2020 Decennial API: https://api.census.gov/data/2020/dec/pl.html
- Variable list: https://api.census.gov/data/2020/dec/pl/variables.html

## Support

If you have issues with the Census API itself (not this repo):
- Email: census.data@census.gov
- API forum: https://gitter.im/uscensusbureau/home

