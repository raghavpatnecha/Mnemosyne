"""
Excel Parser for Excel files (XLSX, XLS)
Converts Excel sheets to markdown tables
"""

import pandas as pd
from typing import Dict, Any


class ExcelParser:
    """Parser for Excel files using pandas and openpyxl"""

    SUPPORTED_FORMATS = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
    }

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        return content_type in self.SUPPORTED_FORMATS

    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to markdown table format

        Args:
            df: pandas DataFrame

        Returns:
            Markdown formatted table string
        """
        if df.empty:
            return ""

        # Try using pandas to_markdown if available (requires tabulate)
        try:
            return df.to_markdown(index=False)
        except (ImportError, AttributeError):
            # Fallback to manual markdown formatting
            return self._manual_markdown_table(df)

    def _manual_markdown_table(self, df: pd.DataFrame) -> str:
        """
        Manually format DataFrame as markdown table

        Args:
            df: pandas DataFrame

        Returns:
            Markdown formatted table string
        """
        lines = []

        # Header row
        headers = [str(col) for col in df.columns]
        lines.append("| " + " | ".join(headers) + " |")

        # Separator row
        lines.append("|" + "|".join([" --- " for _ in headers]) + "|")

        # Data rows
        for _, row in df.iterrows():
            values = [str(val) if pd.notna(val) else "" for val in row]
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse Excel file and convert to markdown tables

        Args:
            file_path: Path to Excel file

        Returns:
            Dict with:
                - content: Markdown formatted tables
                - metadata: Sheet names, row/column counts
                - page_count: Number of sheets
        """
        # Determine engine based on file extension
        engine = 'openpyxl' if file_path.endswith('.xlsx') else None

        # Read all sheets from Excel file
        excel_file = pd.ExcelFile(file_path, engine=engine)
        sheet_names = excel_file.sheet_names

        content_parts = []
        sheet_metadata = []

        for sheet_name in sheet_names:
            # Read the sheet
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine=engine)

            # Skip completely empty sheets
            if df.empty:
                sheet_metadata.append({
                    "sheet_name": sheet_name,
                    "rows": 0,
                    "columns": 0,
                    "column_names": [],
                })
                continue

            # Add sheet header
            content_parts.append(f"## Sheet: {sheet_name}\n")

            # Convert to markdown table
            markdown_table = self._dataframe_to_markdown(df)
            content_parts.append(markdown_table)
            content_parts.append("\n")  # Add spacing between sheets

            # Collect metadata for this sheet
            sheet_metadata.append({
                "sheet_name": sheet_name,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": [str(col) for col in df.columns],
            })

        # Combine all sheets
        content = "\n".join(content_parts)

        metadata = {
            "sheet_count": len(sheet_names),
            "sheet_names": sheet_names,
            "sheets": sheet_metadata,
            "total_rows": sum(sheet["rows"] for sheet in sheet_metadata),
            "total_columns": sum(sheet["columns"] for sheet in sheet_metadata),
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": len(sheet_names),
        }
