# Quick Start - 5 Minutes to First Migration

**Complete beginner?** Follow these exact steps:

## 1. Download This Tool (2 minutes)

**Windows Users:**
1. Click the green "Code" button at the top of this page
2. Click "Download ZIP"
3. Right-click the downloaded file → "Extract All"
4. Open the extracted folder

**Mac Users:**
1. Click the green "Code" button at the top of this page
2. Click "Download ZIP"
3. Double-click the downloaded file to extract it
4. Open the extracted folder

## 2. Install Python (2 minutes)

**Check if you already have Python:**
- Windows: Open "Command Prompt" and type `python --version`
- Mac: Open "Terminal" and type `python3 --version`

If you see a version number like "Python 3.9.1", you're good! Skip to step 3.

**Install Python if you don't have it:**
- Go to [python.org](https://python.org/downloads)
- Click the big yellow "Download Python" button
- Run the downloaded file
- **IMPORTANT:** Check "Add Python to PATH" during installation

## 3. Setup the Tool (1 minute)

**Windows:**
1. In the extracted folder, hold Shift and right-click in empty space
2. Select "Open PowerShell window here" or "Open Command Prompt here"
3. Type these commands:
```bash
pip install -r requirements.txt
copy config\config.example.ini config\config.ini
```

**Mac:**
1. In the extracted folder, right-click and select "Services" → "New Terminal at Folder"
2. Type these commands:
```bash
pip3 install -r requirements.txt
cp config/config.example.ini config/config.ini
```

## 4. Get Your HubSpot Keys (5 minutes)

**You need to do this in BOTH HubSpot accounts:**

1. **Log into your HubSpot account**
2. **Click the Settings gear ⚙️** (top right corner)
3. **Go to "Integrations" → "Private Apps"** (left sidebar)
4. **Click "Create a private app"**
5. **Name it:** "Migration Tool"
6. **Click the "Scopes" tab**
7. **Check these scopes** (organize by category for easier finding):
   
   **CRM Objects:**
   - ☑️ `crm.objects.contacts.read`
   - ☑️ `crm.objects.contacts.write`  
   - ☑️ `crm.objects.companies.read`
   - ☑️ `crm.objects.companies.write`
   - ☑️ `crm.objects.deals.read`
   - ☑️ `crm.objects.deals.write`
   
   **Properties & Schema:**
   - ☑️ `crm.schemas.contacts.read`
   - ☑️ `crm.schemas.contacts.write`
   - ☑️ `crm.schemas.companies.read`
   - ☑️ `crm.schemas.companies.write`
   - ☑️ `crm.schemas.deals.read`
   - ☑️ `crm.schemas.deals.write`
   
   **Associations:**
   - ☑️ `crm.objects.associations.read`
   - ☑️ `crm.objects.associations.write`
8. **Click "Create app"**
9. **Copy the token** (starts with `pat-na1-`)

**Repeat this for your second HubSpot account.**

## 5. Configure the Tool (1 minute)

1. **Open the file:** `config/config.ini` (use Notepad on Windows or TextEdit on Mac)
2. **Replace the example tokens:**

```ini
[hubspot]
production_token = pat-na1-YOUR-FIRST-TOKEN-HERE
sandbox_token = pat-na1-YOUR-SECOND-TOKEN-HERE
```

3. **Save the file**

## 6. Test It (30 seconds)

In your command line/terminal, type:

```bash
python migrate.py --dry-run --limit 3
```

You should see:
```
🚀 HubSpot Modern Migration Tool (2025)
✅ Configuration loaded successfully
🔌 Testing API connectivity...
✅ Production API connection successful
✅ Sandbox API connection successful
```

## 7. Run Your First Migration (1 minute)

```bash
python migrate.py --limit 5
```

🎉 **That's it!** You just migrated 5 contacts between HubSpot accounts!

## What Next?

- **Migrate more contacts:** `python migrate.py --limit 50`
- **Migrate everything:** `python migrate.py`
- **Need help?** Check the logs in the `logs` folder

## Troubleshooting

**"python is not recognized" error?**
- Reinstall Python and make sure to check "Add Python to PATH"

**"Permission denied" error?**
- Make sure your Private Apps have all required scopes checked (15 scopes total for full functionality)

**"No contacts found" error?**
- Check that your source HubSpot account actually has contacts

**Still stuck?**
- Read the full README.md file
- Check the `docs` folder for detailed guides