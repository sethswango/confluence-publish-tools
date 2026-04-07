# Confluence Publish Tools

Publish markdown documents with Mermaid diagrams to Confluence. Renders diagrams as high-quality PNGs, uploads them as page attachments, and publishes in Confluence storage format.

## Requirements

- Python 3.10+
- [pandoc](https://pandoc.org/installing.html) on PATH
- Node.js / npx (for `@mermaid-js/mermaid-cli`)
- `curl.exe` (ships with Windows 10+)

## Usage

### Create a new page

```powershell
python publish_to_confluence.py "path/to/document.md" `
    --space-id 1222049790 `
    --parent-id 26508984338 `
    --email seth.swango@veteransunited.com `
    --token $env:CONFLUENCE_TOKEN
```

### Update an existing page

```powershell
python publish_to_confluence.py "path/to/document.md" `
    --space-id 1222049790 `
    --parent-id 26508984338 `
    --page-id 26509934624 `
    --email seth.swango@veteransunited.com `
    --token $env:CONFLUENCE_TOKEN `
    --message "Updated with latest findings"
```

### Environment variables

Set these to avoid passing auth on every call:

```powershell
$env:CONFLUENCE_EMAIL = "seth.swango@veteransunited.com"
$env:CONFLUENCE_TOKEN = "your-atlassian-pat"
```

## What it does

1. Reads the markdown file
2. Finds all ` ```mermaid ` blocks and renders them to PNG via mermaid-cli (scale 3x, 1200px wide, white background)
3. Strips Obsidian-specific syntax (`[[wikilinks]]`)
4. Converts markdown to HTML via pandoc
5. Replaces `<img>` tags with Confluence `<ac:image>` attachment macros
6. Creates or updates the Confluence page
7. Uploads PNG attachments
8. Updates the page body with storage format so images render

No temp files are left behind.

## Known VU Confluence Targets

| Folder | Space ID | Parent ID |
|--------|----------|-----------|
| AI Doc Processing | 1222049790 | 26508984338 |
