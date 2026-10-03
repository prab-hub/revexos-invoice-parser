# RevExOS Invoice Parser for Claude

Parse invoice PDFs and images into structured data from inside Claude: invoice number, dates,
PO number, vendor and customer, currency, payment terms, subtotal, tax, total, and every line
item. Each result is checked (do the line items add up to the subtotal? does subtotal plus tax
equal the total?) and can be exported as JSON or CSV.

It uses the free [RevExOS Invoice Parser](https://revexos.com/invoice-parser), the same engine
as the website and the [Chrome extension](https://chromewebstore.google.com/detail/revexos-invoice-parser/igddabebdginpkpcgbjfdomdpomlmgio).

Two ways to use it:

| | Skill (this repo) | MCP connector |
|---|---|---|
| Input | A local file Claude can read | A public https link to the file |
| Works in | Claude Code, claude.ai (with network access) | claude.ai, Claude Desktop, Claude Code |
| Limit | 2/day per IP, 5/day with an email | 5/day per email |

## Install

### Claude Code (plugin: skill + MCP connector)

```
/plugin marketplace add prab-hub/revexos-invoice-parser
/plugin install revexos-invoice-parser@revexos-invoice-parser
```

Then ask: *"Parse ~/Downloads/invoice-4471.pdf and save the line items as CSV."*

### claude.ai or Claude Desktop (skill)

1. Download `revexos-invoice-parser.zip` from the [latest release](https://github.com/prab-hub/revexos-invoice-parser/releases/latest).
2. Go to **Settings > Capabilities > Skills**, click **Upload skill**, and choose the zip.
3. Code execution needs to reach `revexos.com`: under **Settings > Capabilities**, allow network access for code execution (all domains, or add `revexos.com` to the allowed list). On Team and Enterprise plans an org owner may have to allow it. If it's blocked, the script fails with `403 Forbidden` / `connect_rejected`.
4. Upload an invoice in a chat and ask Claude to parse it.

### MCP connector only (no skill)

In **Settings > Connectors > Add custom connector**, enter the URL `https://revexos.com/api/mcp`. No sign-in is needed, so the "couldn't determine how this server signs in" note can be skipped with **Continue anyway**
([setup steps](https://revexos.com/mcp)). Claude gets a `parse_invoice` tool that takes a public
file URL and your email.

## Run the script directly

No dependencies beyond Python 3.8+.

```bash
python3 skills/revexos-invoice-parser/scripts/parse_invoice.py examples/sample-invoice.pdf --csv out.csv
```

```json
{
  "invoice": {
    "invoice_number": "NWA-2026-0418",
    "invoice_date": "2026-09-15",
    "due_date": "2026-10-15",
    "po_number": "PO-77310",
    "vendor_name": "Northwind Analytics LLC",
    "currency": "USD",
    "payment_terms": "Net 30",
    "subtotal": 7050,
    "tax": 599.25,
    "total": 7649.25,
    "line_items": [
      { "description": "Revenue dashboard implementation", "quantity": 1, "unit_price": 4500, "amount": 4500, "sku": null }
    ]
  },
  "checks": {
    "line_items_sum": 7050.0,
    "line_items_match_subtotal": true,
    "subtotal_plus_tax_matches_total": true
  }
}
```

(Output trimmed; the real response includes every field and line item.)

Options: `--email you@company.com` (5 parses a day instead of 2), `--json out.json`, `--csv out.csv`.

## Privacy

The file is sent to revexos.com, extracted with GPT-4o, and not stored. RevExOS logs only the
file type, page count, IP and (if given) email, for rate limiting. See the
[privacy policy](https://revexos.com/privacy).

## Limits

- PDF or image up to 3MB with the skill, 10MB with the MCP connector.
- 2 parses per IP per day free, 5 with an email. The MCP connector allows 5 per email per day.

## License

MIT
