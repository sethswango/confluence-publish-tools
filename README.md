# Confluence Publish Tools

Publish markdown documents with Mermaid diagrams to Confluence. Renders diagrams as high-quality PNGs, uploads them as page attachments, and publishes in Confluence storage format.

## Requirements

- Python 3.10+
- [pandoc](https://pandoc.org/installing.html) on PATH
- Node.js / npx (for `@mermaid-js/mermaid-cli`)
- `curl.exe` (ships with Windows 10+)

## Usage

Normal workflow:

- use the real source markdown file as the required file path
- if the Confluence version needs audience-focused cleanup, pass curated content via `--body`
- do not create a workspace staging folder for publish intermediates
- if a temporary staged file is truly unavoidable, use a named `C:\dev\.scratch\sessions\YYYYMMDD-HHMM-confluence-publish\` folder and remove known-owned intermediates after verification

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

## Important usage notes

### Use this script, not MCP page create/update, for Mermaid pages

If the page contains Mermaid diagrams or attachment-backed images, this script is the correct final publish path.

- Atlassian MCP page create/update is fine for plain text pages
- It is not the right final path for Mermaid pages because it does not render Mermaid, upload attachments, or insert Confluence image macros
- Symptom of using the wrong path: the page shows plain text/code instead of rendered diagrams

### Re-publishing pages with the same diagram filenames

Rendered diagrams are named `diagram_1.png`, `diagram_2.png`, etc.

If you re-publish the same page and the diagrams should have changed but Confluence still appears unchanged:

1. Verify the page body via REST (`expand=body.storage`) contains `<ac:image>` / `ri:attachment`
2. If storage is correct but the page still appears stale, inspect the page attachments
3. Delete old `diagram_*.png` attachments and re-run the script so fresh attachments are uploaded

## Preparing content for a team audience

This tool is usually used to publish a cleaned-up version of existing local documentation, not raw personal notes.

When preparing content:

- remove Obsidian-only navigation and vault references
- remove local file paths and note-management chatter
- rewrite private shorthand or colloquial terms into team-readable language
- keep the page tightly topical instead of carrying side blurbs about adjacent notes
- preserve the technical substance: architecture, evidence, tradeoffs, tables, diagrams, and conclusions

Good outcome:
- reads like a page written for the team
- does not read like an exported personal note

## Known VU Confluence Targets

| Folder | Space ID | Parent ID |
|--------|----------|-----------|
| AI Doc Processing | 1222049790 | 26508984338 |
