# Target Extraction schema (invoice)

```json
{
  "$schema": "[http://json-schema.org/draft-01/schema#](http://json-schema.org/draft-01/schema#)",
  "type": "object",
  "properties": {
    "invoice_id": {
      "type": "object",
      "properties": {
        "value": { "type": ["string", "null"] },
        "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      }
    },
    "company": {
      "type": "object",
      "properties": {
        "value": { "type": ["string", "null"], "description": "Company name" },
        "confidence": { "type": "number" }
      }
    },
    "amount": {
      "type": "object",
      "properties": {
        "value": { "type": ["number", "null"], "description": "Total amount as integer/float" },
        "confidence": { "type": "number" }
      }
    },
    "currency": {
      "type": "object",
      "properties": {
        "value": { "type": ["string", "null"], "description": "JPY, USD" },
        "confidence": { "type": "number" }
      }
    },
    "date": {
      "type": "object",
      "properties": {
        "value": { "type": ["string", "null"], "description": "Standardized to YYYY-MM-DD" },
        "confidence": { "type": "number" }
      }
    },
    "line_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": { "type": "string" },
          "quantity": { "type": ["number", "null"] },
          "unit_price": { "type": ["number", "null"] },
          "total": { "type": ["number", "null"] }
        }
      }
    }
  },
  "required": ["invoice_id", "company", "amount", "currency", "date", "line_items"]
}
```
