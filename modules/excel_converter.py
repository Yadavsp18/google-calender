import pandas as pd
import os
import uuid
import json
from datetime import datetime

UPLOAD_FOLDER = "uploads"
JSON_FOLDER = "json_files"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

def convert_excel_to_json(file):
    # Preserve original file extension
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lower()
    base_name = os.path.splitext(original_filename)[0]
    
    excel_filename = str(uuid.uuid4()) + ext
    excel_path = os.path.join(UPLOAD_FOLDER, excel_filename)

    file.save(excel_path)

    try:
        # Use appropriate engine based on file extension
        if ext == ".xlsx":
            df = pd.read_excel(excel_path, engine="openpyxl")
        elif ext == ".xls":
            df = pd.read_excel(excel_path, engine="xlrd")
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        # Convert DataFrame to list of dicts WITHOUT stripping whitespace
        records = df.to_dict(orient="records")
        
        # Convert any datetime objects to string
        def serialize_value(value):
            if isinstance(value, (datetime, pd.Timestamp)):
                return value.strftime("%Y-%m-%d")  # match your Start Date format
            elif pd.isna(value):
                return None
            else:
                return value

        # Wrap keys and values with spaces as in your example
        formatted_records = []
        for record in records:
            new_record = {}
            for key, value in record.items():
                # Add spaces around key (you can customize number of spaces)
                spaced_key = f"{key}"
                
                # Add spaces around string values (match your example)
                if isinstance(value, str):
                    spaced_value = f"{value}"
                else:
                    spaced_value = serialize_value(value)
                
                new_record[spaced_key] = spaced_value
            formatted_records.append(new_record)

        # Save JSON file
        json_filename = base_name + ".json"
        json_path = os.path.join(JSON_FOLDER, json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(formatted_records, f, indent=2)

    finally:
        # Clean up uploaded excel file
        if os.path.exists(excel_path):
            os.remove(excel_path)

    return json_filename
