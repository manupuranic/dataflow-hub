# utils/helpers.py
import csv
import uuid
import datetime
import os
import pandas as pd
import html

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def read_csv(file_path):
    full_path = os.path.join(BASE_DIR, file_path)
    with open(full_path, newline='', encoding='utf-8') as csvfile:
        return list(csv.DictReader(csvfile))
    
def read_data(file_path):
    """
    Reads a CSV or Excel file into a pandas DataFrame,
    skipping any initial blank rows before the header.

    Args:
        file_path (str): Path to the input file (CSV or XLSX).

    Returns:
        pd.DataFrame: Loaded data.

    Raises:
        ValueError: If file type is unsupported.
    """
    import pandas as pd
    import os

    full_path = os.path.join(BASE_DIR, file_path)

    def find_header_row_xlsx(path):
        # Scan first 20 rows to find first non-empty row with header columns
        temp_df = pd.read_excel(path, nrows=20, header=None)
        for idx, row in temp_df.iterrows():
            if row.dropna().shape[0] > 1:  # heuristic: more than 1 non-empty cell = header
                return idx
        return 0

    def find_header_row_csv(path):
        # For CSV, read lines until first line with >1 non-empty column
        with open(path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                if len([c for c in line.strip().split(',') if c]) > 1:
                    return idx
        return 0

    if full_path.endswith(".csv"):
        header_row = find_header_row_csv(full_path)
        df = pd.read_csv(full_path, header=header_row)
    elif full_path.endswith(".xlsx") or full_path.endswith(".xls"):
        header_row = find_header_row_xlsx(full_path)
        df = pd.read_excel(full_path, header=header_row)
    else:
        raise ValueError("Unsupported file type. Use .csv or .xlsx")

    return df

def read_csv_in_chunks(file_path, chunk_size=1000):
    full_path = os.path.join(BASE_DIR, file_path)
    with open(full_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

def read_data_in_chunks(file_path, chunk_size=500):
    full_path = os.path.join(BASE_DIR, file_path)
    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.csv':
        with open(full_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            chunk = []
            for row in reader:
                chunk.append(row)
                if len(chunk) == chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    elif ext == '.xlsx':
        df = pd.read_excel(full_path, dtype=str, engine='openpyxl').fillna('')
        for i in range(0, len(df), chunk_size):
            yield df.iloc[i:i + chunk_size].to_dict(orient='records')

    else:
        raise ValueError("Unsupported file type. Only .csv and .xlsx are supported.")

def generate_id():
    return str(uuid.uuid4())

def now():
    return datetime.datetime.utcnow()

def clean_item_name(name):
    if not name:
        return ''
    # Decode HTML entities like &amp; to &
    name = name.strip()
    
    cleaned = html.unescape(name)
    # Optionally: remove extra whitespace
    # cleaned = ' '.join(cleaned.split())
    return cleaned

def safe_get(value):
    return None if pd.isna(value) else value