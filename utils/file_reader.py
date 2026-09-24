"""
File reading utilities for the AI Supply Chain Control Center.

Handles the three source file types the app accepts:
- Inventory (Excel)
- Shipping (CSV)
- Vendor contracts (PDF)

Each reader validates its input and raises a clear ValueError on
failure so the Streamlit layer can show a friendly message instead
of a raw traceback.
"""

import io

import pandas as pd
from pypdf import PdfReader


def read_inventory(file) -> pd.DataFrame:
    """Read an inventory Excel file into a DataFrame."""
    try:
        df = pd.read_excel(file)
    except Exception as exc:
        raise ValueError(f"Could not read inventory Excel file: {exc}") from exc

    if df.empty:
        raise ValueError("Inventory file was read but contains no rows.")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_shipping(file) -> pd.DataFrame:
    """Read a shipping CSV file into a DataFrame."""
    try:
        df = pd.read_csv(file)
    except Exception as exc:
        raise ValueError(f"Could not read shipping CSV file: {exc}") from exc

    if df.empty:
        raise ValueError("Shipping file was read but contains no rows.")

    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def read_contract(file) -> str:
    """Extract text from a vendor contract PDF."""
    try:
        reader = PdfReader(file)
    except Exception as exc:
        raise ValueError(f"Could not read contract PDF: {exc}") from exc

    pages_text = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        pages_text.append(extracted)

    text = "\n\n".join(pages_text).strip()

    if not text:
        raise ValueError(
            "No extractable text found in this PDF. It may be a scanned "
            "image without OCR text."
        )

    return text


def generate_sample_inventory() -> bytes:
    """Build a small sample inventory workbook, useful for trying the app
    without your own data. Returns raw .xlsx bytes.
    """
    data = {
        "SKU": ["SKU-1001", "SKU-1002", "SKU-1003", "SKU-1004", "SKU-1005"],
        "Item Name": [
            "Steel Bolts (100pk)",
            "Cardboard Boxes (M)",
            "Industrial Sensors",
            "Packing Tape",
            "Aluminum Sheets",
        ],
        "Category": ["Hardware", "Packaging", "Electronics", "Packaging", "Raw Material"],
        "Quantity": [420, 55, 12, 610, 8],
        "Reorder Point": [100, 75, 20, 150, 25],
        "Unit Price": [4.50, 1.20, 89.00, 3.10, 42.00],
        "Warehouse": ["WH-A", "WH-B", "WH-A", "WH-B", "WH-A"],
    }
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventory")
    return buffer.getvalue()


def generate_sample_shipping() -> bytes:
    """Build a small sample shipping CSV, useful for trying the app
    without your own data. Returns raw CSV bytes.
    """
    data = {
        "Shipment ID": ["SHP-001", "SHP-002", "SHP-003", "SHP-004", "SHP-005"],
        "Origin": ["Chennai", "Mumbai", "Shenzhen", "Chennai", "Hamburg"],
        "Destination": ["Bangalore", "Delhi", "Chennai", "Kolkata", "Chennai"],
        "Carrier": ["BlueDart", "DHL", "Maersk", "FedEx", "Maersk"],
        "Ship Date": ["2026-09-01", "2026-09-03", "2026-08-20", "2026-09-10", "2026-08-25"],
        "Expected Delivery Date": [
            "2026-09-04", "2026-09-06", "2026-09-10", "2026-09-13", "2026-09-08",
        ],
        "Actual Delivery Date": [
            "2026-09-04", "2026-09-09", "2026-09-14", "", "2026-09-08",
        ],
        "Status": ["Delivered", "Delivered", "Delivered", "In Transit", "Delivered"],
    }
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def read_suppliers(file) -> pd.DataFrame:
    """Read a supplier directory CSV into a DataFrame.

    Expected to list, for each item, the suppliers who can provide it
    along with lead time, price, and (optionally) a reliability score.
    This is what the Disruption Advisor searches for alternatives.
    """
    try:
        df = pd.read_csv(file)
    except Exception as exc:
        raise ValueError(f"Could not read supplier directory CSV: {exc}") from exc

    if df.empty:
        raise ValueError("Supplier file was read but contains no rows.")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def generate_sample_suppliers() -> bytes:
    """Build a small sample supplier directory that matches the items in
    generate_sample_inventory(), so the Disruption Advisor has real
    alternatives to find. Returns raw CSV bytes.
    """
    data = {
        "Item Name": [
            "Steel Bolts (100pk)", "Steel Bolts (100pk)", "Steel Bolts (100pk)",
            "Cardboard Boxes (M)", "Cardboard Boxes (M)",
            "Industrial Sensors", "Industrial Sensors",
            "Packing Tape", "Packing Tape",
            "Aluminum Sheets", "Aluminum Sheets",
        ],
        "Supplier Name": [
            "Bolt & Fastener Co", "Global Hardware Ltd", "FastFix Industrial",
            "PackRight Supplies", "EcoBox Manufacturing",
            "SensorTech Inc", "PrecisionParts Co",
            "PackRight Supplies", "TapeWorld",
            "MetalWorks Ltd", "SteelAlum Traders",
        ],
        "Location": [
            "Chennai", "Mumbai", "Shenzhen",
            "Chennai", "Bangalore",
            "Bangalore", "Shenzhen",
            "Chennai", "Delhi",
            "Hamburg", "Mumbai",
        ],
        "Lead Time (Days)": [3, 5, 12, 2, 4, 7, 15, 2, 3, 10, 6],
        "Unit Price": [4.50, 4.20, 3.80, 1.20, 1.10, 89.00, 76.00, 3.10, 2.95, 42.00, 45.50],
        "Reliability (1-5)": [4, 5, 3, 4, 4, 5, 3, 4, 4, 5, 4],
    }
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()