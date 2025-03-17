import os
import re
from collections import defaultdict

def get_chapter_files(directory):
    # Dictionary to hold lists of chapter files
    chapter_files = defaultdict(list)
    
    # Regular expression to match chapter files starting with 'chp', 'ch', or 'Chapter'
    chapter_pattern = re.compile(r'^(chp|ch|Chapter)(\d+)(_?[a-zA-Z0-9]*)?\.xhtml$', re.IGNORECASE)
    
    # Iterate through the files in the directory
    for filename in os.listdir(directory):
        match = chapter_pattern.match(filename)
        if match:
            chapter_number = match.group(2)
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            chapter_files[chapter_number].append({'filename': filename, 'content': content})
    
    # Convert defaultdict to a regular dict and return as a list of lists
    return [files for files in chapter_files.values()]

# Example usage
directory_path = './eBooks/epub'  # Replace with the actual path to your sample_files directory
chapter_groups = get_chapter_files(directory_path)
for chapter_group in chapter_groups:
    for chapter in chapter_group:
        print(chapter.get('filename'))
    print()