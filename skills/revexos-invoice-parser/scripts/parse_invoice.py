#!/usr/bin/env python3
"""Parse an invoice (PDF or image) into structured JSON with the RevExOS Invoice Parser API.

Usage:
  python3 parse_invoice.py <file> [--email you@company.com] [--csv out.csv] [--json out.json]

Standard library only. Sends the file to https://revexos.com/api/invoice-parser, which
extracts header fields and line items with GPT-4o. The file is not stored; RevExOS logs
only the file type, page count and your IP for rate limiting.

Free limits: 2 parses per IP per day, 5 per day with --email.
Size limits: PDF up to 3MB, images up to 5MB (convert larger images to JPEG first).
"""

import argparse
import base64
import csv
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API_URL = os.environ.get("REVEXOS_API_URL", "https://revexos.com/api/invoice-parser")
MAX_PDF_BYTES = 3_200_000
MAX_IMAGE_BYTES = 3_200_000  # Vercel caps request bodies at 4.5MB, base64 adds a third
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

HEADER_FIELDS = [
    "invoice_number", "invoice_date", "due_date", "po_number", "vendor_name", "vendor_address",
    "customer_name", "customer_address", "currency", "payment_terms", "subtotal", "tax", "total",
]
LINE_FIELDS = ["description", "quantity", "unit_price", "amount", "sku"]


def fail(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def build_body(path, email):
    with open(path, "rb") as f:
        data = f.read()
    if data[:5] == b"%PDF-":
        if len(data) > MAX_PDF_BYTES:
            fail(f"PDF is {len(data) / 1e6:.1f}MB; the API accepts up to 3MB. Split it or export only the invoice pages.")
        body = {"pdf": "data:application/pdf;base64," + base64.b64encode(data).decode(), "fileType": "pdf"}
    else:
        mime = mimetypes.guess_type(path)[0] or ""
        if mime not in IMAGE_TYPES:
            fail(f"unsupported file type '{mime or 'unknown'}'. Use a PDF, PNG, JPEG, WebP or GIF.")
        if len(data) > MAX_IMAGE_BYTES:
            fail(f"image is {len(data) / 1e6:.1f}MB; the API accepts up to 3MB. Save it as a smaller JPEG first.")
        body = {"images": [f"data:{mime};base64," + base64.b64encode(data).decode()], "fileType": "image"}
    if email:
        body["email"] = email
    return body


def call_api(body):
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "revexos-invoice-parser-skill/1.0",
            "X-RevExOS-Client": "claude-skill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            fail(f"API returned HTTP {e.code}.")
        if err.get("error") == "need_email":
            fail("free limit reached (2/day without email). Re-run with --email you@company.com for 3 more today.", 2)
        fail(err.get("message") or f"API returned HTTP {e.code}.", 2)
    except urllib.error.URLError as e:
        fail(f"could not reach {API_URL} ({e.reason}). If running in a sandbox, allow network access to revexos.com.")


def checks(inv):
    def r(n):
        return round(n + 0.0, 2)
    amounts = [li.get("amount") for li in inv.get("line_items", [])]
    line_sum = r(sum(amounts)) if amounts and all(a is not None for a in amounts) else None
    sub, tax, total = inv.get("subtotal"), inv.get("tax"), inv.get("total")
    return {
        "line_items_sum": line_sum,
        "line_items_match_subtotal": None if line_sum is None or sub is None else r(line_sum - sub) == 0,
        "subtotal_plus_tax_matches_total": None if sub is None or total is None else r(sub + (tax or 0) - total) == 0,
    }


def write_csv(inv, path):
    # One row per line item, header fields repeated, the shape most AP imports expect.
    items = inv.get("line_items") or [{}]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER_FIELDS + ["line_" + k for k in LINE_FIELDS])
        for li in items:
            w.writerow([inv.get(k) for k in HEADER_FIELDS] + [li.get(k) for k in LINE_FIELDS])


def main():
    p = argparse.ArgumentParser(description="Parse an invoice with the RevExOS Invoice Parser API.")
    p.add_argument("file", help="Invoice PDF or image")
    p.add_argument("--email", help="Unlocks 5 parses/day instead of 2")
    p.add_argument("--json", dest="json_out", help="Also write the result to this JSON file")
    p.add_argument("--csv", dest="csv_out", help="Also write line items to this CSV file")
    a = p.parse_args()

    if not os.path.isfile(a.file):
        fail(f"no such file: {a.file}")
    res = call_api(build_body(a.file, a.email))
    inv = res.get("data")
    if not inv:
        fail("the API returned no data.")
    if not inv.get("line_items") and all(inv.get(k) is None for k in HEADER_FIELDS):
        fail("no invoice data was found in that file. Check that it is an invoice and that a scan is legible.", 3)
    out = {"invoice": inv, "checks": checks(inv), "parses_used_today": res.get("usedToday")}

    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    if a.csv_out:
        write_csv(inv, a.csv_out)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
