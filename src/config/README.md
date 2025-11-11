# Configuration Directory

This directory contains application configuration files and credentials.

## Service Account Setup

### Step 1: Get Your Google Service Account Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the Google Sheets API and Google Drive API
4. Go to "IAM & Admin" → "Service Accounts"
5. Create a new service account or select an existing one
6. Click "Keys" → "Add Key" → "Create New Key" → Select "JSON"
7. Download the JSON file

### Step 2: Add Credentials to This Project

1. Copy `service-account.json.example` to `service-account.json`:
   ```bash
   cp src/config/service-account.json.example src/config/service-account.json
   ```

2. Open `service-account.json` and replace its contents with your downloaded JSON file

3. **Important**: The file is automatically git-ignored, so your credentials won't be committed

### Step 3: Share Your Google Sheet

1. Open your Google Sheet
2. Click "Share" in the top right
3. Add the service account email (found in the JSON as `client_email`)
4. Give it "Editor" permissions

### Step 4: Set Environment Variable

Set the `GOOGLE_SHEETS_URL` environment variable to your sheet URL:
- In Replit: Go to Secrets and add `GOOGLE_SHEETS_URL`
- Locally: Add to your `.env` file

## Files in This Directory

- `settings.py` - Main configuration class that loads settings and credentials
- `service-account.json` - Your Google Service Account credentials (git-ignored)
- `service-account.json.example` - Template file showing the expected JSON structure
- `README.md` - This file

## Security Notes

- ✅ `service-account.json` is automatically ignored by git
- ✅ Never commit real credentials to version control
- ✅ Never share your service account JSON publicly
- ✅ Treat it like a password - keep it secret!

## Troubleshooting

**Error: "Service account file not found"**
- Make sure you've created `src/config/service-account.json`
- Check that the file is in the correct location

**Error: "Failed to connect to Google Sheets"**
- Verify your service account email has access to the sheet
- Check that the `GOOGLE_SHEETS_URL` is correct
- Ensure the JSON file is valid (not corrupted)

**Error: "Invalid JSON"**
- Make sure you copied the entire JSON file contents
- Check for any trailing commas or syntax errors
