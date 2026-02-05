# Email Service Database

This directory contains all database-related files for the Email Service.

---

## Directory Structure

```bash
src/email_service/db/
├── README.md                              # This file - overview
├── DEVELOPER_GUIDE.md                     # Guide for adding columns/tables
├── schema/                                # Initial schema for new environments
│   ├── init-schema.sql                    # Complete database schema
│   └── init-schema.sh                     # Script to execute schema via RDS Data API
├── migrations/                            # Alembic migrations for existing environments
│   ├── alembic.ini                        # Alembic configuration
│   ├── env.py                             # Alembic environment (supports RDS Data API)
│   └── versions/                          # Migration scripts
│       └── 20260125_1707_001_add_recipient_name_to_emails.py
└── run_migration_via_rds_data_api.py      # Script to run migrations via RDS Data API
```

---

## Quick Start

### For New Environments (Fresh Database)

Use `init-schema.sql` to create the complete schema from scratch:

Please refer to the [Guide](https://www.notion.so/aws-educate-tw/TPET-Aurora-Serverless-1fd6bfee681780afa405eea9794ec261) in Notion

### For Existing Environments (Schema Changes)

Please refer to the [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for step-by-step instructions on creating and applying Alembic migrations.

---

## When to Use Which

| Scenario | Tool | Files |
|----------|------|-------|
| Setting up a brand new environment | init-schema.sh | `schema/init-schema.sql` |
| Adding column to existing table | Alembic migration | `migrations/versions/XXX.py` |
| Adding new table | Alembic migration | `migrations/versions/XXX.py` |
| Modifying indexes | Alembic migration | `migrations/versions/XXX.py` |

---

## Important: Keep Both in Sync

When you create a new migration, you must also update `schema/init-schema.sql`:

1. **Migration file** - For existing environments (incremental change)
2. **init-schema.sql** - For new environments (complete schema)

This ensures new environments get the complete schema while existing environments only run the delta.

---

## Environment Summary

| Environment | Region | Health Check URL |
|-------------|--------|------------------|
| local-dev | us-west-2 | https://local-dev-email-service-internal-api-tpet.aws-educate.tw/local-dev/email-service/health |
| preview | us-west-1 | https://preview-email-service-internal-api-tpet.aws-educate.tw/preview/email-service/health |
| dev | us-east-1 | https://dev-email-service-internal-api-tpet.aws-educate.tw/dev/email-service/health |
| prod | ap-northeast-1 | https://email-service-internal-api-tpet.aws-educate.tw/prod/email-service/health |

---

## CI/CD Integration

Database migrations are automatically detected and executed in CI/CD:

1. CI/CD detects changes in `src/email_service/db/migrations`
2. Manual approval is required via GitHub Issue
3. After approval, `run_migration_via_rds_data_api.py` is executed
4. Migration status is reported in workflow logs
