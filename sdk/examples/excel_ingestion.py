"""
Excel ingestion example for XLSX and XLS files.

This example demonstrates:
- Ingesting Excel spreadsheets (XLSX, XLS)
- Processing financial reports, data tables, and analytics
- Converting Excel sheets to markdown tables
- Monitoring processing status
- Searching tabular data
- Metadata tagging for spreadsheets
"""

import time
from mnemosyne import Client
from uuid import UUID

# Initialize client
client = Client(api_key="your_api_key_here")


def ingest_financial_reports():
    """Ingest financial Excel reports"""

    print("=" * 60)
    print("FINANCIAL REPORTS INGESTION")
    print("=" * 60)

    # Create collection for financial reports
    collection = client.collections.create(
        name="Financial Reports",
        description="Excel financial statements and reports",
        metadata={"content_type": "excel", "category": "finance"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Excel files to upload
    excel_files = [
        {
            "file": "reports/q1_2024_financial_statement.xlsx",
            "metadata": {
                "title": "Q1 2024 Financial Statement",
                "report_type": "financial_statement",
                "quarter": "Q1",
                "year": 2024,
                "department": "Finance",
                "sheets": ["Income Statement", "Balance Sheet", "Cash Flow"],
            },
        },
        {
            "file": "reports/annual_budget_2024.xlsx",
            "metadata": {
                "title": "2024 Annual Budget",
                "report_type": "budget",
                "year": 2024,
                "department": "Finance",
                "sheets": ["Revenue", "Expenses", "Projections"],
            },
        },
        {
            "file": "reports/expense_analysis_jan_2024.xlsx",
            "metadata": {
                "title": "January 2024 Expense Analysis",
                "report_type": "expense_analysis",
                "month": "January",
                "year": 2024,
                "department": "Accounting",
                "categories": ["operations", "marketing", "engineering"],
            },
        },
    ]

    print("Uploading Excel files...")
    uploaded_files = []
    for excel in excel_files:
        try:
            # SDK detects Excel MIME type and converts sheets to markdown tables
            doc = client.documents.create(
                collection_id=collection.id,
                file=excel["file"],
                metadata=excel["metadata"],
            )
            uploaded_files.append(doc)
            print(f"✓ Queued: {excel['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {excel['file']} (skipping)")
        except Exception as e:
            print(f"✗ Failed to upload: {e}")

    print()

    # Monitor processing progress
    print("Monitoring Excel processing...")
    for doc in uploaded_files:
        while True:
            status = client.documents.get_status(doc.id)

            if status.status == "completed":
                print(f"✓ Processing complete: {doc.id}")
                print(f"  Chunks: {status.chunk_count}")
                print(f"  Tokens: {status.total_tokens}")
                break
            elif status.status == "failed":
                print(f"✗ Processing failed: {status.error_message}")
                break
            else:
                print(f"⏳ Processing... ({status.status})")
                time.sleep(5)

    return collection.id


def ingest_sales_data():
    """Ingest sales and analytics Excel files"""

    print("\n" + "=" * 60)
    print("SALES DATA INGESTION")
    print("=" * 60)

    # Create collection for sales data
    collection = client.collections.create(
        name="Sales Analytics",
        description="Sales data and performance analytics",
        metadata={"content_type": "excel", "category": "sales"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Sales Excel files
    sales_files = [
        {
            "file": "sales/q1_sales_report.xlsx",
            "metadata": {
                "title": "Q1 Sales Report",
                "report_type": "sales_report",
                "quarter": "Q1",
                "year": 2024,
                "metrics": ["revenue", "units_sold", "conversion_rate"],
                "regions": ["North America", "Europe", "Asia"],
            },
        },
        {
            "file": "sales/customer_analysis.xls",
            "metadata": {
                "title": "Customer Segmentation Analysis",
                "report_type": "customer_analysis",
                "year": 2024,
                "segments": ["enterprise", "mid_market", "smb"],
                "metrics": ["ltv", "churn_rate", "acquisition_cost"],
            },
        },
        {
            "file": "sales/pipeline_forecast.xlsx",
            "metadata": {
                "title": "Sales Pipeline Forecast",
                "report_type": "pipeline_forecast",
                "quarter": "Q2",
                "year": 2024,
                "stages": ["prospecting", "qualification", "proposal", "negotiation"],
            },
        },
    ]

    print("Uploading sales Excel files...")
    for excel in sales_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=excel["file"],
                metadata=excel["metadata"],
            )
            print(f"✓ Uploaded: {excel['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {excel['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def ingest_project_data():
    """Ingest project management Excel files"""

    print("\n" + "=" * 60)
    print("PROJECT DATA INGESTION")
    print("=" * 60)

    # Create collection for project data
    collection = client.collections.create(
        name="Project Management",
        description="Project timelines, resources, and tracking",
        metadata={"content_type": "excel", "category": "project_management"},
    )
    print(f"✓ Created collection: {collection.id}\n")

    # Project Excel files
    project_files = [
        {
            "file": "projects/rag_system_timeline.xlsx",
            "metadata": {
                "title": "RAG System Project Timeline",
                "project_name": "RAG System v2",
                "project_status": "in_progress",
                "team_size": 8,
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "phases": ["planning", "development", "testing", "deployment"],
            },
        },
        {
            "file": "projects/resource_allocation.xlsx",
            "metadata": {
                "title": "Q1 Resource Allocation",
                "report_type": "resource_planning",
                "quarter": "Q1",
                "year": 2024,
                "teams": ["Engineering", "Product", "Design"],
            },
        },
    ]

    print("Uploading project Excel files...")
    for excel in project_files:
        try:
            doc = client.documents.create(
                collection_id=collection.id,
                file=excel["file"],
                metadata=excel["metadata"],
            )
            print(f"✓ Uploaded: {excel['metadata']['title']}")
            print(f"  ID: {doc.id}")
        except FileNotFoundError:
            print(f"✗ File not found: {excel['file']} (skipping)")
        except Exception as e:
            print(f"✗ Upload failed: {e}")

    return collection.id


def search_excel_data(collection_id: UUID):
    """Search Excel spreadsheet data"""

    print("\n" + "=" * 60)
    print("SEARCHING EXCEL DATA")
    print("=" * 60)

    queries = [
        "What were the total expenses in Q1 2024?",
        "Show me the revenue breakdown by region",
        "What are the project milestones for the RAG system?",
        "Compare customer acquisition costs across segments",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")

        results = client.retrievals.retrieve(
            query=query,
            mode="hybrid",
            top_k=3,
            collection_id=collection_id,
        )

        print(f"Found {len(results.results)} results:")
        for i, result in enumerate(results.results, 1):
            print(f"\n  {i}. Score: {result.score:.4f}")
            print(f"     File: {result.document.title or result.document.filename}")
            print(f"     Type: {result.document.metadata.get('report_type', 'N/A')}")
            print(f"     Content: {result.content[:200]}...")


def main():
    """Run Excel ingestion examples"""

    print("\nMnemosyne Excel Ingestion Example\n")
    print("Supported formats: XLSX, XLS")
    print("Converts Excel sheets to searchable markdown tables\n")

    # Example 1: Financial reports
    finance_collection_id = ingest_financial_reports()

    # Example 2: Sales data
    sales_collection_id = ingest_sales_data()

    # Example 3: Project management data
    project_collection_id = ingest_project_data()

    # Example 4: Search Excel data
    search_excel_data(finance_collection_id)

    print("\n" + "=" * 60)
    print("EXCEL INGESTION COMPLETE!")
    print("=" * 60)
    print(f"\nFinance Collection ID: {finance_collection_id}")
    print(f"Sales Collection ID: {sales_collection_id}")
    print(f"Project Collection ID: {project_collection_id}")
    print("\nAll Excel files have been processed and are searchable!")
    print("\nNote: Excel processing:")
    print("  - Converts all sheets to markdown tables")
    print("  - Preserves cell values and structure")
    print("  - Enables semantic search across tabular data")
    print("  - Supports formulas (converted to values)")
    print("  - Handles multiple sheets per workbook")
    print("\nBest practices:")
    print("  - Tag sheets with descriptive metadata")
    print("  - Use clear column headers")
    print("  - Keep data organized in tables")
    print("  - Avoid merged cells for better parsing")


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
