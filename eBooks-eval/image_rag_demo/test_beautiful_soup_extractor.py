#!/usr/bin/env python3
"""
Test script to verify BeautifulSoup-based extractor
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from beautiful_soup_extractor import BeautifulSoupImageMetadataExtractor

def test_extractor():
    """Test the BeautifulSoup extractor with different configurations"""
    
    # Test 1: Full paragraphs (default)
    print("=" * 60)
    print("Testing with full paragraphs (default)")
    print("=" * 60)
    extractor = BeautifulSoupImageMetadataExtractor()
    test_single_epub(extractor, "9780323697132")
    
    # Test 2: Limited to 3 sentences
    print("\n" + "=" * 60)
    print("Testing with 3 sentences limit")
    print("=" * 60)
    extractor_limited = BeautifulSoupImageMetadataExtractor(max_sentences=3)
    test_single_epub(extractor_limited, "9780323791984")
    
    # Test 3: Limited to 5 sentences
    print("\n" + "=" * 60)
    print("Testing with 5 sentences limit")
    print("=" * 60)
    extractor_limited_5 = BeautifulSoupImageMetadataExtractor(max_sentences=5)
    test_single_epub(extractor_limited_5, "9780323828451")

def test_single_epub(extractor, isbn):
    """Helper function to test a single EPUB with a given extractor configuration"""
    base_dir = Path("../extracted_epubs")
    epub_dir = base_dir / isbn
    if not epub_dir.exists():
        print(f"EPUB {isbn} not found, skipping...")
        return
        
    print(f"\n{'='*60}")
    print(f"Testing EPUB: {isbn}")
    print(f"{'='*60}")
        
    # Find content directory
    content_dir = None
    for subdir in ['OEBPS', 'OPS']:
        potential_dir = epub_dir / subdir
        if potential_dir.exists():
            content_dir = potential_dir
            break
    
    if not content_dir:
        print(f"No content directory found for {isbn}")
        return
    
    # Find chapter files
    chapter_files = extractor.find_chapter_files(content_dir)
    print(f"Found {len(chapter_files)} chapter files")
    
    # Test first 2 chapters
    for i, chapter_file in enumerate(chapter_files[:2]):
        print(f"\n--- Chapter {i+1}: {chapter_file.name} ---")
        
        try:
            # Read chapter content
            with open(chapter_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse with BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find visual elements
            visual_elements = extractor.find_visual_elements(soup)
            
            if visual_elements:
                print(f"Found {len(visual_elements)} visual elements")
                
                # Count by tag type
                tag_counts = {}
                type_counts = {}
                for visual in visual_elements:
                    tag_name = visual['tag_name']
                    visual_type = visual['type']
                    tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
                    type_counts[visual_type] = type_counts.get(visual_type, 0) + 1
                
                print(f"Tag types: {tag_counts}")
                print(f"Visual types: {type_counts}")
                
                # Show details for first 3 elements
                for j, visual in enumerate(visual_elements[:3]):
                    print(f"\nElement {j+1}:")
                    print(f"  Tag Type: {visual['tag_name']}")
                    print(f"  Visual Type: {visual['type']}")
                    print(f"  ID: {visual['id']}")
                    print(f"  Caption: {visual['caption'][:100]}...")
                    print(f"  Context Text: {visual['context_text'][:200]}...")
            else:
                print("No visual elements found in this chapter")
                
        except Exception as e:
            print(f"Error processing chapter {chapter_file.name}: {e}")

if __name__ == "__main__":
    test_extractor() 