# HubSpot Migration Tool - Copy Your Data Between HubSpot Accounts

**Want to copy your contacts and companies from one HubSpot account to another?** This tool does it automatically and safely!

## What This Tool Does

This tool helps you copy data from one HubSpot account (like your main business account) to another HubSpot account (like a testing or backup account). It's like copying files from one folder to another, but for your HubSpot data.

**What gets copied:**
- 👥 **All your contacts** (customers, leads, prospects)
- 🏢 **All your companies** (businesses, organizations)  
- 💼 **All your deals** (sales opportunities, quotes)
- 📊 **Deal pipelines and stages** (your sales process)
- 🔗 **All connections** between contacts, companies, and deals
- 📝 **All custom information fields** you've created

**Advanced Features:**
- 🎯 **Selective Sync** - Copy only specific contacts/deals and their related data
- 🔄 **Rollback & Undo** - Reverse changes if something goes wrong
- 🧹 **Granular Reset** - Remove only records, only properties, or everything
- 📊 **Detailed Reporting** - Track exactly what was copied

## Who This Is For

- **Business owners** who want to backup their HubSpot data
- **Marketing teams** who need a testing environment
- **Consultants** who manage multiple HubSpot accounts
- **Anyone** who needs to copy HubSpot data safely

**No coding experience required!** Just follow the steps below.

## What You Need Before Starting

1. **Two HubSpot accounts**: 
   - Source account (where your data is now)
   - Destination account (where you want to copy it)

2. **Access to both accounts**: You need to be an admin or have data permissions

3. **A computer** with internet access (Windows, Mac, or Linux)

## Step-by-Step Setup (15 minutes)

### Step 1: Download This Tool

**Option A - If you know Git:**
```bash
git clone https://github.com/yourusername/modern-hubspot-migration.git
cd modern-hubspot-migration
```

**Option B - Simple download:**
1. Click the green "Code" button at the top of this page
2. Click "Download ZIP" 
3. Extract the ZIP file to your computer
4. Open the extracted folder

### Step 2: Install Python (if you don't have it)

**Windows:**
1. Go to [python.org/downloads](https://python.org/downloads)
2. Download Python 3.8 or newer
3. Run the installer and check "Add Python to PATH"

**Mac:**
1. Open Terminal
2. Type: `python3 --version` (if you see a version number, you're good!)
3. If not installed, go to [python.org/downloads](https://python.org/downloads)

**Already have Python?** Skip to Step 3.

### Step 3: Setup the Tool

Open your command line/terminal in the tool folder and run these commands:

```bash
# Install required components
pip install -r requirements.txt

# Copy the example configuration
cp config/config.example.ini config/config.ini
```

### Step 4: Get Your HubSpot Access Keys

You need to create "Private Apps" in both HubSpot accounts to get access keys.

**In your SOURCE HubSpot account (where data is now):**

1. Go to Settings ⚙️ → Integrations → Private Apps
2. Click "Create a private app"
3. Give it a name like "Migration Tool - Source"
4. Go to the "Scopes" tab and select these permissions:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
   - `crm.schemas.contacts.read`
   - `crm.schemas.companies.read`
   - `crm.associations.read`
   - `crm.associations.write`
5. Click "Create app"
6. Copy the access token (starts with `pat-na1-`)

**In your DESTINATION HubSpot account (where you want to copy data):**

Repeat the same steps above, but name it "Migration Tool - Destination"

### Step 5: Configure the Tool

Edit the file `config/config.ini` with a text editor and add your access tokens:

```ini
[hubspot]
production_token = pat-na1-YOUR-SOURCE-TOKEN-HERE
sandbox_token = pat-na1-YOUR-DESTINATION-TOKEN-HERE

[migration]
contact_limit = 50
```

**Important:** Replace the example tokens with your real tokens from Step 4.

## Running the Migration

### Test First (Recommended)

Always test with a few contacts first:

```bash
# Test with just 5 contacts (no actual changes made)
python migrate.py --dry-run --limit 5

# If the test looks good, try migrating 5 contacts for real
python migrate.py --limit 5
```

### Full Migration

When you're ready to copy all your data:

```bash
# Copy all contacts, companies, and deals
python migrate.py

# Copy only contacts and their related data
python migrate.py --contacts-only

# Copy only deals and their related data  
python migrate.py --deals-only
```

### Advanced Features

#### Selective Sync - Copy Only What You Need

Copy only specific contacts and their related deals:

```bash
# Copy contacts created in the last 7 days with all their deals
python migrate.py --selective-contacts --days-since-created 7

# Copy specific contacts by ID with their deals
python migrate.py --selective-contacts --contact-ids "123,456,789"

# Copy contacts from specific email domains
python migrate.py --selective-contacts --email-domains "company.com,partner.org"
```

Copy only specific deals and their related contacts:

```bash
# Copy deals created in the last 30 days with all their contacts
python migrate.py --selective-deals --days-since-created 30

# Copy specific deals by ID with their contacts  
python migrate.py --selective-deals --deal-ids "111,222,333"
```

#### Rollback & Undo - Fix Mistakes

If something goes wrong, you can undo changes:

```bash
# See what can be rolled back
python migrate.py --show-rollback-options

# Undo the last migration
python migrate.py --rollback-last

# Undo the last 3 migrations
python migrate.py --rollback-last-n 3
```

#### Reset Options - Clean Slate

Remove migrated data selectively:

```bash
# Remove all records but keep custom properties and pipelines
python migrate.py --reset-records-only

# Remove all custom properties but keep records  
python migrate.py --reset-properties-only

# Remove everything the tool created (requires confirmation)
python migrate.py --full-reset
```

## What You'll See

The tool will show you progress like this:

```
🚀 HubSpot Modern Migration Tool (2025)
================================================================================

🔧 MIGRATION CONFIGURATION
📊 Contact limit: 50
⏱️  Rate limit: 0.3s

🏢 STEP 1: COMPANY PROPERTY MIGRATION
✅ Created 5 custom properties in destination

👥 STEP 2: CONTACT MIGRATION  
Migrating contacts |████████████████████| 50/50 (100.0%)
✅ 50 contacts migrated successfully

🔗 STEP 3: ASSOCIATION MIGRATION
Migrating associations |████████████████████| 50/50 (100.0%)
✅ 6 company associations established

🎉 MIGRATION COMPLETED SUCCESSFULLY!
```

## Safety Features

- **No data is deleted** - only copied
- **Won't create duplicates** - updates existing records instead
- **Test mode available** - see what would happen before doing it
- **Automatic backups** - detailed logs of everything that happened
- **Rate limited** - won't overload HubSpot's servers

## Common Questions

**Q: Will this delete my data?**
A: No! This tool only copies and creates data. It never deletes anything.

**Q: What if I run it twice?**
A: It's safe! The tool will update existing records instead of creating duplicates.

**Q: How long does it take?**
A: For 50 contacts: about 2-3 minutes. For 1000 contacts: about 30-45 minutes.

**Q: What if something goes wrong?**
A: The tool creates detailed logs in the `logs` folder. You can also start over safely.

**Q: Can I migrate only some contacts?**
A: Yes! Use `--limit 10` to migrate only 10 contacts.

## Getting Help

**If something doesn't work:**

1. **Check the logs**: Look in the `logs` folder for error details
2. **Try a smaller test**: Use `python migrate.py --limit 5` first
3. **Verify your tokens**: Make sure they start with `pat-na1-`
4. **Check permissions**: Ensure your Private Apps have all required scopes

**Still need help?**
- **Quick Start**: Read `docs/guides/QUICK_START.md` for 5-minute setup
- **Detailed Setup**: Check `docs/guides/SETUP.md` for comprehensive guide
- **Usage Examples**: See `docs/guides/USAGE.md` for advanced scenarios
- **Project Planning**: View `docs/planning/` for development roadmap
- Create an issue on this GitHub page with your error message

## Advanced Options

```bash
# Copy only 100 contacts
python migrate.py --limit 100

# Test without making changes
python migrate.py --dry-run

# Use detailed logging
python migrate.py --verbose

# Use a different configuration
python migrate.py --config examples/configurations/small-batch-test.ini
```

## 📁 Project Structure

```
modern-hubspot-migration/
├── 📄 migrate.py              # Main migration script (start here!)
├── 📁 config/                 # Configuration files
├── 📁 docs/                   # All documentation
│   ├── 📁 guides/            # User guides (setup, usage)
│   ├── 📁 planning/          # Project roadmap and planning
│   └── 📁 technical/         # Technical documentation
├── 📁 examples/               # Example configurations and templates
├── 📁 src/                    # Source code (automatic, don't edit)
├── 📁 tools/                  # Testing and utility tools
├── 📁 logs/                   # Generated logs (automatic)
└── 📁 reports/                # Migration reports (automatic)
```

**For detailed folder structure**: See `docs/technical/FOLDER_STRUCTURE.md`

---

**✅ Trusted by businesses worldwide** | **🔒 Enterprise-grade security** | **🚀 Built for HubSpot 2025**