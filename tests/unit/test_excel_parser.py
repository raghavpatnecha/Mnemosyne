"""
Unit tests for ExcelParser

Tests:
- MIME type validation (can_parse)
- Single sheet parsing
- Multi-sheet parsing
- Empty sheet handling
- Metadata extraction (sheet names, row/column counts)
- Markdown table formatting
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

from backend.parsers.excel_parser import ExcelParser


@pytest.mark.unit
class TestExcelParser:
    """Test suite for ExcelParser"""

    async def test_can_parse_xlsx(self):
        """Test can_parse with XLSX MIME type"""
        parser = ExcelParser()
        assert parser.can_parse(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ) is True

    async def test_can_parse_xls(self):
        """Test can_parse with XLS MIME type"""
        parser = ExcelParser()
        assert parser.can_parse("application/vnd.ms-excel") is True

    async def test_can_parse_invalid_pdf(self):
        """Test can_parse rejects PDF MIME type"""
        parser = ExcelParser()
        assert parser.can_parse("application/pdf") is False

    async def test_can_parse_invalid_text(self):
        """Test can_parse rejects text MIME type"""
        parser = ExcelParser()
        assert parser.can_parse("text/plain") is False

    async def test_can_parse_invalid_csv(self):
        """Test can_parse rejects CSV MIME type"""
        parser = ExcelParser()
        assert parser.can_parse("text/csv") is False

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_single_sheet(self, mock_read_excel, mock_excel_file_class):
        """Test parsing Excel file with single sheet"""
        # Setup ExcelFile mock
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        # Create test dataframe
        test_df = pd.DataFrame({
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Age': [25, 30, 35],
            'City': ['New York', 'San Francisco', 'Boston']
        })
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/test.xlsx")

        # Verify content includes sheet header
        assert "## Sheet: Sheet1" in result["content"]
        assert "Name" in result["content"]
        assert "Age" in result["content"]
        assert "Alice" in result["content"]
        assert "Bob" in result["content"]

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["sheet_count"] == 1
        assert metadata["sheet_names"] == ["Sheet1"]
        assert metadata["total_rows"] == 3
        assert metadata["total_columns"] == 3

        # Verify sheet metadata
        sheet_info = metadata["sheets"][0]
        assert sheet_info["sheet_name"] == "Sheet1"
        assert sheet_info["rows"] == 3
        assert sheet_info["columns"] == 3
        assert sheet_info["column_names"] == ['Name', 'Age', 'City']

        # Verify page count
        assert result["page_count"] == 1

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_multi_sheet(self, mock_read_excel, mock_excel_file_class):
        """Test parsing Excel file with multiple sheets"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sales", "Inventory", "Summary"]
        mock_excel_file_class.return_value = mock_excel_file

        # Create test dataframes for each sheet
        sales_df = pd.DataFrame({
            'Product': ['Widget', 'Gadget'],
            'Revenue': [1000, 2000]
        })
        inventory_df = pd.DataFrame({
            'Item': ['Widget', 'Gadget'],
            'Stock': [50, 30]
        })
        summary_df = pd.DataFrame({
            'Metric': ['Total Sales', 'Total Items'],
            'Value': [3000, 80]
        })

        mock_read_excel.side_effect = [sales_df, inventory_df, summary_df]

        parser = ExcelParser()
        result = await parser.parse("/fake/path/workbook.xlsx")

        # Verify all sheets are in content
        assert "## Sheet: Sales" in result["content"]
        assert "## Sheet: Inventory" in result["content"]
        assert "## Sheet: Summary" in result["content"]
        assert "Widget" in result["content"]
        assert "Gadget" in result["content"]

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["sheet_count"] == 3
        assert metadata["sheet_names"] == ["Sales", "Inventory", "Summary"]
        assert metadata["total_rows"] == 6  # 2 + 2 + 2
        assert metadata["total_columns"] == 6  # 2 + 2 + 2
        assert result["page_count"] == 3

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_empty_sheet(self, mock_read_excel, mock_excel_file_class):
        """Test parsing Excel file with empty sheet"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["EmptySheet"]
        mock_excel_file_class.return_value = mock_excel_file

        # Create empty dataframe
        empty_df = pd.DataFrame()
        mock_read_excel.return_value = empty_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/empty.xlsx")

        # Empty sheet should not appear in content
        assert "## Sheet: EmptySheet" not in result["content"]

        # But should be tracked in metadata
        metadata = result["metadata"]
        assert metadata["sheet_count"] == 1
        assert metadata["total_rows"] == 0
        assert metadata["total_columns"] == 0

        sheet_info = metadata["sheets"][0]
        assert sheet_info["sheet_name"] == "EmptySheet"
        assert sheet_info["rows"] == 0
        assert sheet_info["columns"] == 0
        assert sheet_info["column_names"] == []

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_mixed_empty_and_data_sheets(self, mock_read_excel, mock_excel_file_class):
        """Test parsing with mix of empty and data sheets"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Data", "Empty", "MoreData"]
        mock_excel_file_class.return_value = mock_excel_file

        data_df = pd.DataFrame({'Col1': [1, 2]})
        empty_df = pd.DataFrame()
        more_data_df = pd.DataFrame({'Col2': [3, 4]})

        mock_read_excel.side_effect = [data_df, empty_df, more_data_df]

        parser = ExcelParser()
        result = await parser.parse("/fake/path/mixed.xlsx")

        # Only non-empty sheets in content
        assert "## Sheet: Data" in result["content"]
        assert "## Sheet: Empty" not in result["content"]
        assert "## Sheet: MoreData" in result["content"]

        # All sheets in metadata
        metadata = result["metadata"]
        assert metadata["sheet_count"] == 3
        assert metadata["total_rows"] == 4  # 2 + 0 + 2
        assert len(metadata["sheets"]) == 3

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    async def test_dataframe_to_markdown_with_tabulate(self, mock_read_excel, mock_excel_file_class):
        """Test markdown conversion using pandas to_markdown"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        test_df = pd.DataFrame({
            'A': [1, 2],
            'B': [3, 4]
        })
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/test.xlsx")

        # Should contain markdown table markers
        assert "|" in result["content"]
        assert "---" in result["content"] or "A" in result["content"]

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    async def test_dataframe_to_markdown_fallback(self, mock_read_excel, mock_excel_file_class):
        """Test markdown conversion fallback when to_markdown not available"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        # Create dataframe and remove to_markdown method
        test_df = pd.DataFrame({
            'Name': ['Alice'],
            'Age': [25]
        })

        # Mock to_markdown to raise ImportError (tabulate not installed)
        def mock_to_markdown(*args, **kwargs):
            raise ImportError("tabulate not installed")

        test_df.to_markdown = mock_to_markdown
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/test.xlsx")

        # Should still produce markdown table using fallback
        content = result["content"]
        assert "| Name | Age |" in content
        assert "|" in content
        assert "---" in content
        assert "Alice" in content

    async def test_manual_markdown_table(self):
        """Test manual markdown table formatting"""
        parser = ExcelParser()

        df = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Score': [95, 87],
            'Grade': ['A', 'B']
        })

        markdown = parser._manual_markdown_table(df)

        # Check table structure
        lines = markdown.split('\n')
        assert len(lines) == 4  # header + separator + 2 data rows
        assert '| Name | Score | Grade |' in lines[0]
        assert '---' in lines[1]
        assert '| Alice | 95 | A |' in lines[2]
        assert '| Bob | 87 | B |' in lines[3]

    async def test_manual_markdown_table_with_nan(self):
        """Test manual markdown table with NaN values"""
        parser = ExcelParser()

        df = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Email': ['alice@test.com', None]
        })

        markdown = parser._manual_markdown_table(df)

        # NaN should be converted to empty string
        assert 'alice@test.com' in markdown
        assert '| Bob |  |' in markdown or '| Bob | |' in markdown

    async def test_manual_markdown_table_empty(self):
        """Test manual markdown table with empty dataframe"""
        parser = ExcelParser()

        empty_df = pd.DataFrame()
        markdown = parser._manual_markdown_table(empty_df)

        # Empty DataFrame produces header with no columns
        assert "|  |" in markdown or markdown == "|  |\n||"

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_xlsx_engine(self, mock_read_excel, mock_excel_file_class):
        """Test correct engine selection for XLSX files"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        test_df = pd.DataFrame({'A': [1]})
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        await parser.parse("/fake/path/test.xlsx")

        # Should use openpyxl engine for .xlsx
        mock_excel_file_class.assert_called_with("/fake/path/test.xlsx", engine='openpyxl')

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_xls_engine(self, mock_read_excel, mock_excel_file_class):
        """Test correct engine selection for XLS files"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        test_df = pd.DataFrame({'A': [1]})
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        await parser.parse("/fake/path/old_format.xls")

        # Should use None (default) engine for .xls
        mock_excel_file_class.assert_called_with("/fake/path/old_format.xls", engine=None)

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_special_characters_in_data(self, mock_read_excel, mock_excel_file_class):
        """Test parsing with special characters in data"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        test_df = pd.DataFrame({
            'Name': ['Alice & Bob', 'Charlie | Dave'],
            'Symbol': ['$100', '€50']
        })
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/special.xlsx")

        # Special characters should be preserved
        assert 'Alice & Bob' in result["content"]
        assert '$100' in result["content"]
        assert '€50' in result["content"]

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_numeric_column_names(self, mock_read_excel, mock_excel_file_class):
        """Test parsing with numeric column names"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["Sheet1"]
        mock_excel_file_class.return_value = mock_excel_file

        # DataFrame with numeric column names
        test_df = pd.DataFrame({
            0: ['A', 'B'],
            1: ['C', 'D'],
            2: ['E', 'F']
        })
        mock_read_excel.return_value = test_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/numeric_cols.xlsx")

        # Numeric columns should be converted to strings
        metadata = result["metadata"]
        assert metadata["sheets"][0]["column_names"] == ['0', '1', '2']
        assert '| 0 | 1 | 2 |' in result["content"] or '0' in result["content"]

    @patch('backend.parsers.excel_parser.pd.ExcelFile')
    @patch('backend.parsers.excel_parser.pd.read_excel')
    @pytest.mark.asyncio
    async def test_parse_large_sheet(self, mock_read_excel, mock_excel_file_class):
        """Test parsing large sheet with many rows"""
        mock_excel_file = MagicMock()
        mock_excel_file.sheet_names = ["LargeSheet"]
        mock_excel_file_class.return_value = mock_excel_file

        # Create large dataframe
        large_df = pd.DataFrame({
            'ID': range(1000),
            'Value': range(1000, 2000)
        })
        mock_read_excel.return_value = large_df

        parser = ExcelParser()
        result = await parser.parse("/fake/path/large.xlsx")

        metadata = result["metadata"]
        assert metadata["total_rows"] == 1000
        assert metadata["total_columns"] == 2
        assert metadata["sheets"][0]["rows"] == 1000
