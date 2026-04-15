# ZeroStream App URLs Configuration

## Current Deployed URLs

**Frontend (ZeroStream):**
```
https://zerostream-2847375137997282.aws.databricksapps.com
```

**Backend (ZeroBackend):**
```
[TO BE FILLED AFTER DEPLOYMENT]
```

## How to Find Your App URLs

1. **After deploying**, run:
   ```bash
   databricks apps list
   ```

2. **Or check in Databricks UI:**
   - Go to your workspace
   - Navigate to "Compute" → "Apps"
   - Find your app names and copy the URLs

## Important: Update Configuration After Deployment

After deploying both apps, you MUST update the URLs in two places:

### 1. Update config.env
```bash
# Edit config.env and set:
FRONTEND_URL=https://zerostream-[YOUR-FRONTEND-ID].aws.databricksapps.com
BACKEND_URL=https://zerobackend-[YOUR-BACKEND-ID].aws.databricksapps.com
```

### 2. Set Backend URL in Frontend App
The frontend needs to know where the backend is. After deployment:

```bash
# Set the backend URL as an environment variable for the frontend app
databricks apps update zerostream \
  --env BACKEND_URL=https://zerobackend-[YOUR-BACKEND-ID].aws.databricksapps.com
```

Or set it in the Databricks Apps UI:
1. Go to Apps → zerostream → Settings
2. Add environment variable: `BACKEND_URL` = `[your backend URL]`

## Why URLs Change

- Databricks assigns unique IDs to each app deployment
- These IDs are not predictable and change with each new deployment
- The format is: `https://[app-name]-[unique-id].aws.databricksapps.com`

## Troubleshooting

If you see errors like:
- "Backend URL not configured"
- "Backend connection failed"

This means the BACKEND_URL environment variable is not set in the frontend app.

## Testing the Connection

After setting up the URLs:

1. **Test Frontend:**
   ```bash
   curl https://zerostream-2847375137997282.aws.databricksapps.com/api/health
   ```

2. **Test Backend (replace with your URL):**
   ```bash
   curl https://zerobackend-[YOUR-ID].aws.databricksapps.com/api/health
   ```

3. **Test Data Flow:**
   - Open frontend on mobile
   - Check if data appears in backend dashboard
   - Query database to verify data insertion