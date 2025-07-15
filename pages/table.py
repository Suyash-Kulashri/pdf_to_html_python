import camelot
import os

# Define the PDF file path (use raw string to avoid escape sequence issues)
file_path = "../ENG-LCM300-235-02-11-06-24 (Copy).pdf"

# Ensure the file exists
if not os.path.exists(file_path):
    print(f"Error: The file {file_path} does not exist.")
    exit(1)

# Output directory for CSV files
output_dir = "tables_output"
os.makedirs(output_dir, exist_ok=True)

try:
    # Extract tables using Camelot with 'lattice' flavor for well-defined tables
    # You can switch to 'stream' if tables lack clear borders
    tables = camelot.read_pdf(file_path, flavor='lattice', pages='all')
    
    # Print the number of tables found
    print(f"Total tables extracted: {tables.n}")

    if tables.n == 0:
        print("No tables found in the PDF. Try adjusting Camelot settings (e.g., flavor='stream').")
    else:
        # Iterate through each table
        for table_idx, table in enumerate(tables, start=1):
            # Print the table as a Pandas DataFrame
            print(f"\nTable {table_idx} (Page {table.page}):")
            print(table.df)
            
            # Export each table as a CSV
            csv_file = os.path.join(output_dir, f"table_{table_idx}_page_{table.page}.csv")
            table.to_csv(csv_file)
            print(f"Saved table {table_idx} to {csv_file}")
        
        # Optionally, export all tables as a zip file
        zip_file = os.path.join(output_dir, "all_tables.zip")
        tables.export(os.path.join(output_dir, "all_tables.csv"), f='csv', compress=True)
        print(f"Exported all tables to {zip_file}")

except Exception as e:
    print(f"Error processing PDF: {e}")