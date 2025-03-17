import os
import re
import zipfile
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import PatternFill

def extract_epub(epub_path, extract_to):
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def get_chapter_files_exclude(directory):
    # Dictionary to hold lists of chapter files
    chapter_files = defaultdict(list)
    remaining_files = []
    
    # Regular expression to match unwanted files
    unwanted_patterns = [
        re.compile(r'^(cover|title|acknowledgements|dedication|toc|index|about|preface|prologue)\.xhtml$', re.IGNORECASE),
        # Add more patterns as needed
    ]
    
    # Regular expression to match chapter files starting with 'chp', 'ch', 'Chapter', or 'Ch'
    chapter_pattern = re.compile(r'^(chp|ch|Chapter|Ch|B97|c00)(\d+.*)\.xhtml$', re.IGNORECASE)
    
    # Function to recursively search for XHTML files
    def search_xhtml_files(current_dir):
        for root, _, files in os.walk(current_dir):
            for filename in files:
                if filename.endswith('.xhtml'):
                  match=chapter_pattern.match(filename)
                  if match:
                    chapter_number = match.group(2)
                    file_path = os.path.join(root, filename)
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    chapter_files[chapter_number].append({'filename': filename, 'filepath': file_path, 'content': content})
                  else:
                    remaining_files.append(filename)
                    # is_unwanted = any(pattern.match(filename) for pattern in unwanted_patterns)
                    # if not is_unwanted:
                    #     match = chapter_pattern.match(filename)
                    #     if match:
                    #         chapter_number = match.group(2)
                    #         file_path = os.path.join(root, filename)
                    #         with open(file_path, 'r', encoding='utf-8') as file:
                    #             content = file.read()
                    #         chapter_files[chapter_number].append({'filename': filename, 'filepath': file_path, 'content': content})
                    #     else:
                    #         remaining_files.append(filename)
                else:
                    print(f'File is unwanted: {filename}')
    
    # Search for XHTML files in the main directory and subdirectories
    search_xhtml_files(directory)
    
    # Convert defaultdict to a regular dict and return as a list of lists
    return [files for files in chapter_files.values()], remaining_files

def process_epub_files(epub_files, extract_base_dir):
    all_chapters = {}
    for epub_file in epub_files:
        extract_to = os.path.join(extract_base_dir, os.path.splitext(os.path.basename(epub_file))[0])
        extract_epub(epub_file, extract_to)
        
        # Check for both OEBPS and OPS directories
        xhtml_dir = None
        source_dir = None
        for possible_dir in ['OEBPS', 'OPS']:
            possible_path = os.path.join(extract_to, possible_dir, 'xhtml')
            print(f'Checking for xhtml directory: {possible_path}')
            if os.path.exists(possible_path):
                xhtml_dir = possible_path
                source_dir = possible_dir
                print(f'Found xhtml directory: {xhtml_dir}')
                break
        
        if xhtml_dir and os.path.exists(xhtml_dir):
            chapter_groups, remaining_files = get_chapter_files_exclude(xhtml_dir)
            all_chapters[os.path.basename(epub_file)] = (chapter_groups, remaining_files, source_dir)
        else:
            print(f'No xhtml directory found in {epub_file}')
    
    return all_chapters

def write_to_excel(all_chapters, output_file):
    wb = Workbook()
    ws = wb.active
    
    # Define a fill for highlighting
    highlight_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    
    for col, (epub_file, (chapter_groups, remaining_files, source_dir)) in enumerate(all_chapters.items(), start=1):
        header_cell = ws.cell(row=1, column=col, value=epub_file)
        if source_dir == 'OPS':
            header_cell.fill = highlight_fill
        row = 2
        for chapter_group in chapter_groups:
            for chapter in chapter_group:
                ws.cell(row=row, column=col, value=chapter.get('filename'))
                row += 1
        # Insert an empty row to separate chapters and remaining files
        row += 1
        for remaining_file in remaining_files:
            ws.cell(row=row, column=col, value=remaining_file)
            row += 1
    
    wb.save(output_file)

# Example usage
epub_directory = '../../../Downloads/eBooks/'  # Directory containing .epub files
extract_base_dir = './eBooks/extracted_epubs'  # Directory to extract the .epub files
output_file = 'epub_flip_logic.xlsx'  # Output Excel file

# Get list of .epub files from the directory
epub_files = [os.path.join(epub_directory, f) for f in os.listdir(epub_directory) if f.endswith('.epub')]

# Process the EPUB files
all_chapters = process_epub_files(epub_files, extract_base_dir)

# Write the results to an Excel file
write_to_excel(all_chapters, output_file)