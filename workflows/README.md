# Workflows

Sanitized n8n exports. Import in this order:

1. `99-error-handler.json`
2. `01-main.json`
3. `02-stripe-payment-webhook.json`
4. `03-expire-holds.json`

After importing, open every node that shows a warning and re-select your own credential, Airtable base and table, and Google calendar. The files contain placeholders (`REPLACE_WITH_YOUR_CREDENTIAL`, `YOUR_CALENDAR_ID`, `YOUR_WASSENGER_DEVICE_ID`), not working IDs. Imported workflows are inactive: activate `02` and `03` first, then `01`.

## How these files were produced

1. In n8n: open a workflow, three-dot menu, **Download**. Save the raw file in `workflows/raw/` (this folder is git-ignored).
2. Scan and sanitize: `python scripts/check_workflow.py --fix workflows/raw/*.json`
3. Open the `.sanitized.json` file in a text editor, search for your own phone number, email, `sk_`, `Bearer` and `pat`, and confirm nothing remains.
4. Rename it (for example `01-main.json`) and move it into this folder.
