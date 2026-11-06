"""Read the documented holdings CSV format without storing uploaded files."""

import csv
from io import StringIO


REQUIRED_COLUMNS = {"symbol", "quantity", "price", "asset_type"}
OPTIONAL_COLUMNS = {"asset_class", "expense_ratio"}
MAX_UPLOAD_BYTES = 1_000_000
MAX_HOLDINGS = 1_000
CSV_TEMPLATE = (
    "symbol,quantity,price,asset_type,asset_class,expense_ratio\n"
    "VTI,5,250,ETF,STOCKS,0.0003\n"
    "BND,3,72,Bond ETF,BONDS,0.0003\n"
)


def parse_holdings_csv(content: bytes) -> list[dict[str, object]]:
    """Parse CSV numbers; shared portfolio analysis validates financial values.

    Expense ratios in files are fractions: 0.0003 means 0.03%, as in CLI JSON.
    Blank optional cells are omitted, preserving unknown rather than zero fees.
    """
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("CSV must be 1 MB or smaller")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must use UTF-8 encoding") from error
    try:
        reader = csv.DictReader(StringIO(text, newline=""), strict=True)
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields):
            raise ValueError("CSV column names must not be repeated")
        if not REQUIRED_COLUMNS <= set(fields):
            raise ValueError("CSV requires symbol, quantity, price, and asset_type columns")
        unknown = set(fields) - REQUIRED_COLUMNS - OPTIONAL_COLUMNS
        if unknown:
            raise ValueError(f"Unrecognized CSV columns: {', '.join(sorted(unknown))}")
        holdings = []
        for row in reader:
            if None in row:
                raise ValueError(f"CSV line {reader.line_num}: too many fields")
            if not any(value and value.strip() for value in row.values()):
                continue
            if len(holdings) >= MAX_HOLDINGS:
                raise ValueError(f"CSV must contain no more than {MAX_HOLDINGS} holdings")
            holding = {}
            for field, value in row.items():
                value = (value or "").strip()
                if field in OPTIONAL_COLUMNS and not value:
                    continue
                if field in ("quantity", "price", "expense_ratio"):
                    try:
                        holding[field] = float(value)
                    except ValueError as error:
                        raise ValueError(f"CSV line {reader.line_num}: '{field}' must be a number") from error
                else:
                    holding[field] = value
            holdings.append(holding)
    except csv.Error as error:
        raise ValueError("CSV is malformed; check quotes and column separators") from error
    if not holdings:
        raise ValueError("CSV must contain at least one holding")
    return holdings
