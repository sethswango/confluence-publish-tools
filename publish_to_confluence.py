#!/usr/bin/env python3
"""Publish a markdown document with Mermaid diagrams to Confluence.

Renders Mermaid blocks to high-quality PNGs, uploads them as page attachments,
and publishes the full document in Confluence storage format.

Requirements:
  - pandoc on PATH (or at default Windows install location)
  - npx available (for @mermaid-js/mermaid-cli)
  - Python 3.10+

Usage:
  python publish_to_confluence.py <markdown-file> \\
      --space-id 1222049790 \\
      --parent-id 26508984338 \\
      --email seth.swango@veteransunited.com \\
      --token <ATLASSIAN_PAT>

  Or set env vars: CONFLUENCE_EMAIL, CONFLUENCE_TOKEN

  To update an existing page instead of creating:
      --page-id 26509934624
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONFLUENCE_DOMAIN = "vuconfluence.atlassian.net"
CONFLUENCE_API = f"https://{CONFLUENCE_DOMAIN}/wiki/rest/api/content"
PANDOC_PATHS = [
    "pandoc",
    r"C:\Users\seth.swango\AppData\Local\Pandoc\pandoc.exe",
]


def find_pandoc() -> str:
    for p in PANDOC_PATHS:
        try:
            subprocess.run([p, "--version"], capture_output=True, check=True)
            return p
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise SystemExit("pandoc not found. Install from https://pandoc.org/installing.html")


def auth_header(email: str, token: str) -> str:
    return base64.b64encode(f"{email}:{token}".encode()).decode()


def render_mermaid_to_png(mermaid_code: str, output_path: Path) -> bool:
    mmd_path = output_path.with_suffix(".mmd")
    mmd_path.write_text(mermaid_code, encoding="utf-8")
    result = subprocess.run(
        ["npx", "--yes", "@mermaid-js/mermaid-cli",
         "-i", str(mmd_path), "-o", str(output_path),
         "-b", "white", "-s", "3", "-w", "1200"],
        capture_output=True, check=False, shell=True,
    )
    mmd_path.unlink(missing_ok=True)
    return result.returncode == 0 and output_path.exists()


def auto_sanitize(md: str) -> str:
    """Apply only mechanical, non-lossy transformations. Anything requiring
    judgment about what to keep vs. remove is handled by the agent BEFORE
    calling this script, by passing a pre-sanitized string via --body."""
    # [[wikilinks]] -> plain text (mechanical — Confluence can't render these)
    md = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", md)
    md = re.sub(r"\[\[([^\]]+)\]\]", r"\1", md)
    # ![[embedded images]] -> remove (Obsidian-only embed syntax)
    md = re.sub(r"!\[\[([^\]]+)\]\]", "", md)
    # Obsidian callout syntax -> plain blockquote
    md = re.sub(r"^>\s*\[!(\w+)\]\s*", r"> **\1:** ", md, flags=re.MULTILINE)
    # Clean up triple+ blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def markdown_to_html(md_text: str, pandoc: str) -> str:
    result = subprocess.run(
        [pandoc, "--from=gfm", "--to=html5"],
        input=md_text.encode("utf-8"),
        capture_output=True, check=True,
    )
    return result.stdout.decode("utf-8")


def upload_attachment(page_id: str, file_path: Path, auth: str) -> bool:
    result = subprocess.run(
        ["curl.exe", "-s", "-w", "%{http_code}", "-X", "POST",
         f"{CONFLUENCE_API}/{page_id}/child/attachment",
         "-H", f"Authorization: Basic {auth}",
         "-H", "X-Atlassian-Token: nocheck",
         "-F", f"file=@{file_path}",
         "-F", "minorEdit=true"],
        capture_output=True, text=True, check=False,
    )
    status = result.stdout.strip()[-3:] if result.stdout else "???"
    return status == "200"


def create_page(space_id: str, parent_id: str, title: str, body: str, auth: str) -> str:
    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "parentId": parent_id,
        "body": {"representation": "storage", "value": body},
    }
    result = subprocess.run(
        ["curl.exe", "-s", "-X", "POST",
         f"https://{CONFLUENCE_DOMAIN}/wiki/api/v2/pages",
         "-H", f"Authorization: Basic {auth}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, check=False,
    )
    data = json.loads(result.stdout)
    if "id" in data:
        return data["id"]
    raise RuntimeError(f"Page creation failed: {result.stdout[:500]}")


def get_page_version(page_id: str, auth: str) -> int:
    result = subprocess.run(
        ["curl.exe", "-s", f"{CONFLUENCE_API}/{page_id}?expand=version",
         "-H", f"Authorization: Basic {auth}"],
        capture_output=True, text=True, check=False,
    )
    return json.loads(result.stdout)["version"]["number"]


def update_page(page_id: str, title: str, body: str, version: int, auth: str, message: str = "") -> bool:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({
            "version": {"number": version, "message": message or "Updated via publish script"},
            "title": title,
            "type": "page",
            "body": {"storage": {"value": body, "representation": "storage"}},
        }, f, ensure_ascii=False)
        payload_path = f.name

    try:
        result = subprocess.run(
            ["curl.exe", "-s", "-w", "\n%{http_code}", "-X", "PUT",
             f"{CONFLUENCE_API}/{page_id}",
             "-H", f"Authorization: Basic {auth}",
             "-H", "Content-Type: application/json",
             "-d", f"@{payload_path}"],
            capture_output=True, text=True, check=False,
        )
        return "200" in result.stdout.split("\n")[-1]
    finally:
        Path(payload_path).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Publish markdown to Confluence with Mermaid diagram support")
    parser.add_argument("markdown_file", type=Path, help="Path to the markdown file")
    parser.add_argument("--space-id", required=True, help="Confluence space ID (numeric)")
    parser.add_argument("--parent-id", required=True, help="Parent page or folder ID")
    parser.add_argument("--page-id", help="Existing page ID to update (omit to create new)")
    parser.add_argument("--title", help="Page title (defaults to first H1 in markdown)")
    parser.add_argument("--email", default=os.environ.get("CONFLUENCE_EMAIL", ""), help="Atlassian email")
    parser.add_argument("--token", default=os.environ.get("CONFLUENCE_TOKEN", ""), help="Atlassian PAT")
    parser.add_argument("--message", default="", help="Version message for updates")
    parser.add_argument("--diagram-width", type=int, default=800, help="Width for diagram images in Confluence")
    parser.add_argument("--body", help="Pre-sanitized markdown string to use instead of reading the file. "
                                       "The file is still required for Mermaid rendering context but its "
                                       "text content is replaced by this string.")
    args = parser.parse_args()

    if not args.email or not args.token:
        parser.error("--email and --token required (or set CONFLUENCE_EMAIL / CONFLUENCE_TOKEN)")

    if not args.markdown_file.exists():
        parser.error(f"File not found: {args.markdown_file}")

    pandoc = find_pandoc()
    auth = auth_header(args.email, args.token)

    if args.body:
        md = args.body
    else:
        md = args.markdown_file.read_text(encoding="utf-8")

    md = auto_sanitize(md)

    if not args.title:
        title_match = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        args.title = title_match.group(1).strip() if title_match else args.markdown_file.stem

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # Render Mermaid diagrams
        mermaid_blocks = list(re.finditer(r"```mermaid\n(.*?)```", md, re.DOTALL))
        png_files: list[Path] = []
        print(f"Found {len(mermaid_blocks)} Mermaid diagrams")

        for i, match in enumerate(reversed(mermaid_blocks)):
            idx = len(mermaid_blocks) - 1 - i
            png_path = tmp_dir / f"diagram_{idx + 1}.png"
            code = match.group(1).strip()

            if render_mermaid_to_png(code, png_path):
                png_files.append(png_path)
                md = md[:match.start()] + f"![diagram_{idx + 1}.png](diagram_{idx + 1}.png)" + md[match.end():]
                print(f"  Rendered diagram_{idx + 1}.png ({png_path.stat().st_size // 1024} KB)")
            else:
                md = md[:match.start()] + f"> **[Diagram {idx + 1}]** Mermaid rendering failed. See source markdown." + md[match.end():]
                print(f"  WARNING: diagram_{idx + 1} failed to render")

        # Strip Obsidian syntax
        md = re.sub(r"\[\[([^\]]+)\]\]", r"\1", md)

        # Convert to HTML
        print("Converting to Confluence storage format...")
        html = markdown_to_html(md, pandoc)

        # Replace img tags with ac:image macros
        for i in range(len(mermaid_blocks)):
            html = re.sub(
                rf'<img src="diagram_{i + 1}\.png"[^/]*/?>',
                f'<ac:image ac:width="{args.diagram_width}">'
                f'<ri:attachment ri:filename="diagram_{i + 1}.png" /></ac:image>',
                html,
            )

        # Create or identify the page
        if args.page_id:
            page_id = args.page_id
            print(f"Updating existing page {page_id}...")
        else:
            print("Creating new page...")
            page_id = create_page(args.space_id, args.parent_id, args.title, html, auth)
            print(f"  Created page {page_id}")

        # Upload attachments
        if png_files:
            print(f"Uploading {len(png_files)} attachments...")
            for png in sorted(png_files):
                ok = upload_attachment(page_id, png, auth)
                print(f"  {png.name} -> {'OK' if ok else 'already exists or failed'}")

        # Update page with storage format (needed for ac:image macros)
        if args.page_id:
            version = get_page_version(page_id, auth)
            ok = update_page(page_id, args.title, html, version + 1, auth, args.message)
        else:
            version = get_page_version(page_id, auth)
            if version == 1 and png_files:
                ok = update_page(page_id, args.title, html, 2, auth, args.message or "Added diagrams")
            else:
                ok = True

        if ok:
            url = f"https://{CONFLUENCE_DOMAIN}/wiki/spaces/SS/pages/{page_id}"
            print(f"\nPublished: {url}")
        else:
            print("\nWARNING: Page update may have failed. Check Confluence.")


if __name__ == "__main__":
    main()
