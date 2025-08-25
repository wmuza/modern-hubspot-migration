# 📁 Repository Folder Structure

This document explains the organized folder structure of the HubSpot Migration Tool repository.

## 🏗️ **ROOT STRUCTURE**

```
modern-hubspot-migration/
├── 📁 src/                     # Source code
├── 📁 config/                  # Configuration files
├── 📁 docs/                    # Documentation
├── 📁 examples/                # Example files and demos
├── 📁 tools/                   # Development and testing tools
├── 📁 logs/                    # Generated logs (gitignored)
├── 📁 reports/                 # Migration reports (gitignored)
├── 📄 migrate.py              # Main migration script
├── 📄 requirements.txt        # Python dependencies
├── 📄 README.md              # Main project documentation
├── 📄 CHANGELOG.md           # Version history
└── 📄 LICENSE                # MIT License
```

## 📂 **DETAILED FOLDER BREAKDOWN**

### **`src/` - Source Code**
```
src/
├── core/                      # Core system components
│   ├── config.py             # Configuration management
│   └── field_filters.py     # Property filtering system
├── migrations/               # Migration modules
│   ├── contact_migration.py
│   ├── company_property_migrator.py
│   └── enterprise_association_migrator.py
├── utils/                    # Utility functions
│   ├── utils.py             # Common utilities
│   └── debug_contacts.py    # Debug tools
└── validators/               # Data validation
    └── verify_company_properties.py
```

**Purpose**: All production source code organized by function
**Access**: Used by main migration script and tools

### **`config/` - Configuration Files**
```
config/
├── config.example.ini        # Example configuration template
└── config.ini              # User configuration (gitignored)
```

**Purpose**: Secure configuration management
**Security**: Real config files are gitignored

### **`docs/` - Documentation**
```
docs/
├── planning/                 # Project planning documents
│   ├── MISSION_ROADMAP.md   # Complete project roadmap
│   ├── NEXT_PHASE_PLAN.md   # Current phase execution plan
│   └── MISSION_OVERVIEW.md  # Strategic vision
├── guides/                   # User documentation
│   ├── QUICK_START.md       # 5-minute setup guide
│   ├── SETUP.md            # Detailed installation guide
│   └── USAGE.md            # Usage examples and scenarios
├── technical/               # Technical documentation
│   └── FOLDER_STRUCTURE.md # This document
└── images/                  # Screenshots and diagrams
```

**Purpose**: Comprehensive project documentation
**Audience**: Users, developers, and stakeholders

### **`examples/` - Examples and Demos**
```
examples/
├── configurations/          # Example configuration files
│   ├── production-to-staging.ini
│   └── small-batch-test.ini
└── migrations/              # Example migration scenarios
    └── (future migration examples)
```

**Purpose**: Real-world examples and templates
**Usage**: Copy and customize for specific needs

### **`tools/` - Development Tools**
```
tools/
├── testing/                 # Testing utilities
│   └── simple_migrate.py   # Basic connectivity test
├── utilities/               # Development utilities
│   └── property_sync.py    # Legacy property sync tool
└── scripts/                # Automation scripts
    └── (future development scripts)
```

**Purpose**: Development, testing, and maintenance tools
**Audience**: Developers and advanced users

### **`logs/` - Generated Logs (Gitignored)**
```
logs/
├── migration_20250825_140438.log
├── hubspot_migration_20250825_140920.log
└── (all log files are automatically generated)
```

**Purpose**: Runtime logging and debugging
**Security**: Automatically gitignored to prevent data leaks

### **`reports/` - Migration Reports (Gitignored)**
```
reports/
├── migration_report_20250825_142602.json
├── property_mappings_20250825.json
└── (all report files are automatically generated)
```

**Purpose**: Migration results and analytics
**Security**: Automatically gitignored to prevent data leaks

## 🔒 **SECURITY CONSIDERATIONS**

### **Gitignored Folders**
- `logs/` - Contains portal-specific data
- `reports/` - Contains migration results
- `config/config.ini` - Contains API tokens

### **Public Folders**
- `docs/` - Safe for public sharing
- `examples/` - No sensitive data
- `src/` - Clean, secure code only

## 📋 **FOLDER CONVENTIONS**

### **Naming Conventions**
- **Folders**: lowercase with underscores (`snake_case`)
- **Python files**: lowercase with underscores (`snake_case.py`)
- **Documentation**: UPPERCASE with underscores (`UPPER_CASE.md`)
- **Config files**: lowercase with extensions (`.ini`, `.json`)

### **File Organization Rules**
1. **One purpose per folder** - each folder has a clear responsibility
2. **Logical grouping** - related files stay together
3. **Easy navigation** - intuitive folder names
4. **Security by design** - sensitive data automatically separated

### **Adding New Files**

**New migration module** → `src/migrations/`
**New utility function** → `src/utils/`
**New documentation** → `docs/guides/` or `docs/technical/`
**New example** → `examples/configurations/` or `examples/migrations/`
**New tool** → `tools/testing/` or `tools/utilities/`

## 🚀 **BENEFITS OF THIS STRUCTURE**

### **For Developers**
- **Easy navigation** - find files quickly
- **Clear separation** - know where to put new code
- **Logical organization** - understand project layout instantly
- **Scalable architecture** - structure grows with project

### **For Users**
- **Simple entry point** - `README.md` and `migrate.py`
- **Clear documentation** - organized in `docs/`
- **Easy examples** - templates in `examples/`
- **Safe operation** - sensitive data automatically protected

### **For Maintenance**
- **Reduced clutter** - everything in its place
- **Easy cleanup** - clear separation of generated vs source files
- **Professional appearance** - clean, organized repository
- **Future-proof** - structure supports growth

## 📈 **FOLDER EVOLUTION**

As the project grows, new folders may be added:

```
Future additions:
├── tests/                    # Automated test suites
├── docker/                   # Containerization files
├── scripts/                  # Automation and deployment
├── api/                      # API server code (Phase 8)
├── frontend/                 # Web interface code (Phase 8)
└── deploy/                   # Deployment configurations
```

---

**This folder structure is designed for:**
- ✅ **Professional organization**
- ✅ **Security by default**
- ✅ **Easy navigation**
- ✅ **Scalable growth**
- ✅ **Clear separation of concerns**