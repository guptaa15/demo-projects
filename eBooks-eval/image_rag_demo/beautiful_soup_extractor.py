#!/usr/bin/env python3
"""
BeautifulSoup-based Image Metadata Extractor
Extracts visual elements from EPUB XHTML files using BeautifulSoup
"""

import os
import json
import logging
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BeautifulSoupImageMetadataExtractor:
    def __init__(self, base_dir: str = "../extracted_epubs", max_sentences: int = None):
        self.base_dir = Path(base_dir)
        self.max_sentences = max_sentences  # None means capture full paragraphs
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('image_extraction.log')
            ]
        )
        global logger
        logger = logging.getLogger(__name__)
    
    def extract_isbn_from_path(self, epub_path: Path) -> str:
        """Extract ISBN from EPUB directory path"""
        return epub_path.name
    
    def get_output_dir_for_isbn(self, isbn: str) -> Path:
        """Get output directory for a specific ISBN"""
        output_dir = Path("image_metadata_output") / isbn
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def extract_chapter_number(self, filename: str) -> str:
        """Extract chapter number from filename"""
        # Look for chapter patterns
        patterns = [
            r'chp(\d+)', r'chapter(\d+)', r'ch(\d+)', r'chap(\d+)',
            r'chp(\d{3,4})', r'ch(\d{3,4})',  # Handle padded numbers like 001, 002
            r'(\d{3,4})', r'(\d+)'  # Fallback patterns
        ]
        
        filename_lower = filename.lower()
        for pattern in patterns:
            match = re.search(pattern, filename_lower)
            if match:
                chapter_num = match.group(1)
                # Remove leading zeros for cleaner chapter numbers
                return str(int(chapter_num)) if chapter_num.isdigit() else chapter_num
        
        # If no pattern found, try to extract from the filename
        # Handle cases like "CHP003.xhtml" -> "3"
        if 'chp' in filename_lower:
            # Extract numbers after 'chp'
            match = re.search(r'chp(\d+)', filename_lower)
            if match:
                return str(int(match.group(1)))
        
        return "000"
    
    def is_icon_image(self, element) -> bool:
        """Check if an image is an icon (should be filtered out)"""
        # Handle both img and figure elements
        if element.name == 'img':
            # Get alt-text
            alt_text = element.get('alt', '').strip()
            
            # Get figure caption
            figure_caption = ""
            if element.parent and element.parent.name == 'figure':
                figcaption = element.parent.find('figcaption')
                if figcaption:
                    figure_caption = figcaption.get_text(strip=True)
            
            # Rule 1: If alt-text is "image" and figure caption is empty, discard
            if alt_text.lower() == 'image' and not figure_caption:
                return True
            
            # Rule 2: If alt-text is empty but figure caption is present, keep it
            if not alt_text and figure_caption:
                return False
            
            # Rule 3: If both alt-text and figure caption are empty, discard
            if not alt_text and not figure_caption:
                return True
            
            # Rule 4: If alt-text is generic (icon, img) and no figure caption, discard
            if alt_text.lower() in ['icon', 'img'] and not figure_caption:
                return True
            
            # Keep all other images
            return False
            
        elif element.name == 'figure':
            # Check if figure contains an img with problematic alt-text
            img_element = element.find('img')
            if img_element:
                return self.is_icon_image(img_element)
            
            # If no img in figure, check if it has a figcaption
            figcaption = element.find('figcaption')
            if not figcaption:
                return True  # Discard figures without captions
            
            return False
        
        return False
    
    def extract_copyright_info(self, element, context_text: str = "") -> str:
        """Extract copyright and attribution information from visual element and context"""
        try:
            copyright_info = []
            
            # Get caption information
            caption_info = self.extract_caption_info(element)
            figure_caption = caption_info.get("figure_caption", "")
            
            # Combine figure caption and context text for analysis
            text_to_analyze = f"{figure_caption} {context_text}".strip()
            
            # Look for complete attribution statements
            patterns = [
                r'From\s+[^\.]+?(?=\.|$)',  # "From [source]"
                r'Courtesy\s+[^\.]+?(?=\.|$)',  # "Courtesy [source]"
                r'Adapted\s+from\s+[^\.]+?(?=\.|$)',  # "Adapted from [source]"
                r'Source\s*:\s*[^\.]+?(?=\.|$)',  # "Source: [source]"
                r'\(From\s+[^\)]+\)',  # "(From [source])"
                r'\(Courtesy\s+[^\)]+\)',  # "(Courtesy [source])"
                r'\(Adapted\s+from\s+[^\)]+\)',  # "(Adapted from [source])"
                r'©\s*\d{4}\s+[^\.]+?(?=\.|$)',  # "© 2024 [source]"
                r'Copyright\s+\d{4}\s+[^\.]+?(?=\.|$)',  # "Copyright 2024 [source]"
                r'https?://[^\s\)\.]+',  # URLs
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
                if matches:
                    copyright_info.extend(matches)
            
            # If no patterns found, look for sentences containing attribution keywords
            if not copyright_info:
                attribution_keywords = ['from', 'courtesy', 'adapted', 'source', '©', 'copyright']
                sentences = text_to_analyze.split('.')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        sentence_lower = sentence.lower()
                        if any(keyword in sentence_lower for keyword in attribution_keywords):
                            # Check if it's a meaningful attribution (not just the keyword)
                            if len(sentence.split()) > 2:  # More than just the keyword
                                copyright_info.append(sentence)
            
            # Remove duplicates and clean up
            copyright_info = list(set(copyright_info))
            copyright_info = [info.strip() for info in copyright_info if info.strip()]
            
            return " | ".join(copyright_info) if copyright_info else ""
            
        except Exception as e:
            logger.error(f"Error extracting copyright info: {e}")
            return ""
    
    def extract_caption_info(self, element) -> dict:
        """Extract alt-text and figure caption separately"""
        try:
            alt_text = ""
            figure_caption = ""
            source_path = ""
            
            # Extract alt-text
            if element.get('alt'):
                alt_text = element.get('alt').strip()
            
            # Extract title as fallback for alt-text
            if not alt_text and element.get('title'):
                alt_text = element.get('title').strip()
            
            # Extract source path for images
            if element.get('src'):
                source_path = element.get('src').strip()
            
            # Extract figure caption
            if element.name == 'figure':
                figcaption = element.find('figcaption')
                if figcaption:
                    figure_caption = figcaption.get_text(strip=True)
            
            # Look for caption in parent figure (for img elements)
            if element.name == 'img' and element.parent and element.parent.name == 'figure':
                figcaption = element.parent.find('figcaption')
                if figcaption:
                    figure_caption = figcaption.get_text(strip=True)
            
            # For tables, extract table caption
            if element.name == 'table':
                table_caption = element.find('caption')
                if table_caption:
                    figure_caption = table_caption.get_text(strip=True)
            
            return {
                "alt_text": alt_text if alt_text else "",
                "figure_caption": figure_caption if figure_caption else "",
                "source_path": source_path if source_path else ""
            }
            
        except Exception as e:
            logger.error(f"Error extracting caption info: {e}")
            return {"alt_text": "", "figure_caption": "", "source_path": ""}
    
    def extract_caption(self, element) -> str:
        """Extract combined caption from the visual element (for backward compatibility)"""
        caption_info = self.extract_caption_info(element)
        
        # Combine alt-text and figure caption
        parts = []
        if caption_info["alt_text"]:
            parts.append(caption_info["alt_text"])
        if caption_info["figure_caption"]:
            parts.append(caption_info["figure_caption"])
        
        return " | ".join(parts) if parts else "..."
    
    def extract_table_text_content(self, table_element) -> str:
        """Extract all text content from table rows and columns"""
        try:
            table_text = []
            
            # Extract table caption if present
            caption = table_element.find('caption')
            if caption:
                table_text.append(caption.get_text(strip=True))
            
            # Extract headers from thead
            thead = table_element.find('thead')
            if thead:
                header_rows = thead.find_all('tr')
                for row in header_rows:
                    headers = row.find_all(['th', 'td'])
                    header_text = [cell.get_text(strip=True) for cell in headers if cell.get_text(strip=True)]
                    if header_text:
                        table_text.append(" | ".join(header_text))
            
            # Extract data from tbody
            tbody = table_element.find('tbody')
            if tbody:
                data_rows = tbody.find_all('tr')
                for row in data_rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
                    if row_text:
                        table_text.append(" | ".join(row_text))
            
            # If no tbody, look for rows directly
            if not tbody:
                rows = table_element.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
                    if row_text:
                        table_text.append(" | ".join(row_text))
            
            return " | ".join(table_text) if table_text else "Table content"
            
        except Exception as e:
            logger.error(f"Error extracting table text: {e}")
            return "Table content"
    
    def extract_table_html(self, table_element) -> str:
        """Extract the HTML structure of the table for recreation"""
        try:
            # Convert the table element to a string, preserving its structure
            table_html = str(table_element)
            return table_html
        except Exception as e:
            logger.error(f"Error extracting table HTML: {e}")
            return ""
    
    def extract_context_text(self, element, soup) -> str:
        """Extract paragraph text that appears immediately before the visual element"""
        try:
            # Find the paragraph text that immediately precedes this visual element
            preceding_text = ""
            
            # Method 1: Look for previous paragraph tags
            current = element.previous_sibling
            while current:
                if hasattr(current, 'name') and current.name == 'p':
                    text = current.get_text(strip=True)
                    if text and len(text) > 20:
                        preceding_text = self.get_complete_sentences(text, self.max_sentences)
                        break
                current = current.previous_sibling
            
            # Method 2: Look for text in the same parent container
            if not preceding_text:
                parent = element.parent
                if parent:
                    # Get all text from parent
                    parent_text = parent.get_text(strip=True)
                    element_text = element.get_text(strip=True)
                    
                    if element_text and element_text in parent_text:
                        # Split by element text and get the part before it
                        parts = parent_text.split(element_text)
                        if len(parts) > 1:
                            before_text = parts[0].strip()
                            if before_text:
                                preceding_text = self.get_complete_sentences(before_text, self.max_sentences)
            
            # Method 3: Look for text in the entire document before this element
            if not preceding_text:
                # Get the position of this element in the document
                all_elements = soup.find_all()
                element_index = -1
                for i, elem in enumerate(all_elements):
                    if elem == element:
                        element_index = i
                        break
                
                if element_index > 0:
                    # Get text from elements before this one
                    text_before = ""
                    for i in range(max(0, element_index - 5), element_index):
                        elem = all_elements[i]
                        if hasattr(elem, 'get_text'):
                            text = elem.get_text(strip=True)
                            if text and len(text) > 10:
                                text_before += text + " "
                    
                    if text_before:
                        preceding_text = self.get_complete_sentences(text_before, self.max_sentences)
            
            # Method 4: Look for text nodes that come before this element
            if not preceding_text:
                # Find all text nodes in the document
                text_nodes = soup.find_all(text=True)
                element_text = element.get_text(strip=True)
                
                # Find the position of this element's text
                for i, text_node in enumerate(text_nodes):
                    if element_text in text_node.string:
                        # Get text from previous text nodes
                        if i > 0:
                            preceding_text = text_nodes[i-1].string.strip()
                            if not preceding_text and i > 1:
                                preceding_text = text_nodes[i-2].string.strip()
                        break
            
            # Clean up the text
            if preceding_text:
                # Remove extra whitespace and normalize
                preceding_text = re.sub(r'\s+', ' ', preceding_text).strip()
                
                # Remove duplicate phrases (common issue with chapter titles)
                words = preceding_text.split()
                if len(words) > 10:
                    # Check for repeated phrases
                    for i in range(len(words) - 5):
                        phrase = ' '.join(words[i:i+5])
                        if preceding_text.count(phrase) > 1:
                            # Remove the duplicate
                            preceding_text = preceding_text.replace(phrase, '', 1)
                            preceding_text = re.sub(r'\s+', ' ', preceding_text).strip()
                            break
                
                return preceding_text
            else:
                return "Visual element in chapter content."
                
        except Exception as e:
            logger.error(f"Error extracting context text: {e}")
            return "Visual element in chapter content."
    
    def is_complete_sentence(self, sentence: str) -> bool:
        """Check if a sentence is complete and meaningful"""
        if not sentence or len(sentence.strip()) < 10:
            return False
        
        # Check for incomplete patterns
        incomplete_patterns = [
            r'^[a-z]+\s*,?\s*$',  # Single word followed by comma
            r'^[0-9]+\s*$',  # Starts with number
            r'^[ivxlcdm]+\s*$',  # Roman numerals
            r'^[•\-\*]\s*$',  # Bullet points
            r'^[A-Z]\s*$',  # Single letter
            r'^[A-Z][A-Z\s]+\s*$',  # All caps (likely headers)
        ]
        
        for pattern in incomplete_patterns:
            if re.match(pattern, sentence.strip(), re.IGNORECASE):
                return False
        
        # Must have some actual content
        if re.match(r'^[^\w]*$', sentence):
            return False
        
        return True
    
    def split_into_sentences(self, text: str) -> list:
        """Split text into complete sentences"""
        if not text:
            return []
        
        # More sophisticated sentence splitting that preserves complete sentences
        # Look for sentence endings followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Clean and filter sentences
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10 and self.is_complete_sentence(sentence):
                clean_sentences.append(sentence)
        
        return clean_sentences
    
    def get_complete_sentences(self, text: str, max_sentences: int = None) -> str:
        """Get complete sentences from text, optionally limited by count"""
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            return ""
        
        if max_sentences is None:
            # Return all sentences (full paragraph)
            return " ".join(sentences)
        else:
            # Return the last N complete sentences
            return " ".join(sentences[-max_sentences:])
    
    def detect_visual_type(self, element) -> str:
        """Detect the type of visual element"""
        tag_name = element.name.lower()
        
        if tag_name == 'table':
            return 'table'
        elif tag_name == 'img':
            # Check alt-text and caption for clues
            alt_text = element.get('alt', '').lower()
            caption = self.extract_caption(element).lower()
            
            if 'chart' in alt_text or 'chart' in caption:
                return 'chart'
            elif 'graph' in alt_text or 'graph' in caption:
                return 'graph'
            elif 'diagram' in alt_text or 'diagram' in caption:
                return 'diagram'
            elif 'plot' in alt_text or 'plot' in caption:
                return 'plot'
            elif 'figure' in alt_text or 'figure' in caption:
                return 'figure'
            else:
                return 'image'
        elif tag_name == 'figure':
            return 'figure'
        elif tag_name in ['svg', 'canvas']:
            return 'diagram'
        else:
            return 'visual'
    
    def find_visual_elements(self, soup) -> list:
        """Find all visual elements in the HTML using BeautifulSoup"""
        visual_elements = []
        
        # Find all relevant tags
        visual_tags = soup.find_all(['img', 'figure', 'table', 'svg', 'canvas'])
        
        for element in visual_tags:
            # Skip icon images and problematic figures
            if self.is_icon_image(element):
                continue
            
            # Extract basic information
            visual_type = self.detect_visual_type(element)
            caption_info = self.extract_caption_info(element)
            context_text = self.extract_context_text(element, soup)
            copyright_info = self.extract_copyright_info(element, context_text)
            
            # Generate unique ID
            element_id = f"{visual_type}_{len(visual_elements) + 1}"
            
            visual_elements.append({
                'element': element,
                'type': visual_type,
                'id': element_id,
                'caption': caption_info,
                'context_text': context_text,
                'copyright_info': copyright_info,
                'tag_name': element.name
            })
        
        return visual_elements
    
    def find_chapter_files(self, content_dir: Path) -> list:
        """Find all chapter files in the content directory"""
        chapter_files = []
        
        # First, try to get chapters from table of contents
        toc_chapters = self.get_chapters_from_toc(content_dir)
        if toc_chapters:
            logger.info(f"Found {len(toc_chapters)} chapters from table of contents")
            return toc_chapters
        
        # Fallback to pattern-based detection
        logger.info("Using pattern-based chapter detection")
        for file_path in content_dir.rglob("*.xhtml"):
            if self.is_chapter_file(file_path):
                chapter_files.append(file_path)
        
        return sorted(chapter_files)
    
    def get_chapters_from_toc(self, content_dir: Path) -> list:
        """Extract chapter files from table of contents"""
        try:
            # Look for toc.ncx file
            toc_file = content_dir / "toc.ncx"
            if toc_file.exists():
                return self.parse_toc_ncx(toc_file, content_dir)
            
            # Look for nav.xhtml file
            nav_file = content_dir / "nav.xhtml"
            if nav_file.exists():
                return self.parse_nav_xhtml(nav_file, content_dir)
            
            return []
            
        except Exception as e:
            logger.error(f"Error parsing table of contents: {e}")
            return []
    
    def parse_toc_ncx(self, toc_file: Path, content_dir: Path) -> list:
        """Parse toc.ncx file to find chapter files"""
        try:
            with open(toc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all navPoint elements that reference XHTML files
            import re
            chapter_files = []
            
            # Look for href attributes that point to XHTML files
            href_pattern = r'href="([^"]*\.xhtml)"'
            matches = re.findall(href_pattern, content)
            
            for href in matches:
                # Convert href to file path
                file_path = content_dir / "xhtml" / href
                if file_path.exists() and self.is_chapter_file(file_path):
                    chapter_files.append(file_path)
            
            return sorted(chapter_files)
            
        except Exception as e:
            logger.error(f"Error parsing toc.ncx: {e}")
            return []
    
    def parse_nav_xhtml(self, nav_file: Path, content_dir: Path) -> list:
        """Parse nav.xhtml file to find chapter files"""
        try:
            with open(nav_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            chapter_files = []
            
            # Find all links that point to XHTML files
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and href.endswith('.xhtml'):
                    # Convert href to file path
                    file_path = content_dir / "xhtml" / href
                    if file_path.exists() and self.is_chapter_file(file_path):
                        chapter_files.append(file_path)
            
            return sorted(chapter_files)
            
        except Exception as e:
            logger.error(f"Error parsing nav.xhtml: {e}")
            return []
    
    def is_chapter_file(self, file_path: Path) -> bool:
        """Check if a file is a chapter file"""
        filename = file_path.name.lower()
        
        # DEFINITE NON-CHAPTERS (skip these)
        skip_patterns = [
            'nav', 'toc', 'contents', 'index', 'glossary', 
            'preface', 'acknowledgments', 'ack', 'acknowledgments',
            'copyright', 'cover', 'title', 'dedication', 'reviewers',
            'contributors', 'appendix', 'app', 'idx', 'gls', 'rev',
            'pre', 'ded', 'cop', 'cov'
        ]
        
        for pattern in skip_patterns:
            if pattern in filename:
                return False
        
        # DEFINITE CHAPTERS (include these)
        chapter_patterns = [
            'chp', 'chapter', 'chap', 'ch'
        ]
        
        for pattern in chapter_patterns:
            if pattern in filename:
                return True
        
        # AMBIGUOUS CASES (need content analysis)
        # Files like 'SEC001.xhtml' - check content
        if 'sec' in filename:
            return self.has_substantial_content(file_path)
        
        # If no clear pattern, check content to determine if it's a chapter
        return self.has_substantial_content(file_path)
    
    def has_substantial_content(self, file_path: Path) -> bool:
        """Check if file has substantial content (not just navigation)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text_content = soup.get_text()
            
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Check for substantial content
            if len(text_content) < 500:  # Too short to be a chapter
                return False
            
            # Check for navigation-like content
            nav_indicators = ['table of contents', 'contents', 'navigation', 'menu']
            text_lower = text_content.lower()
            for indicator in nav_indicators:
                if indicator in text_lower:
                    return False
            
            # Check for chapter-like structure
            chapter_indicators = ['chapter', 'learning objectives', 'introduction', 'conclusion']
            for indicator in chapter_indicators:
                if indicator in text_lower:
                    return True
            
            # If file has substantial text and no navigation indicators, likely a chapter
            return len(text_content) > 1000
            
        except Exception as e:
            logger.error(f"Error checking content for {file_path}: {e}")
            return False
    
    def process_chapter_file(self, file_path: Path, isbn: str, epub_dir: Path, content_dir: Path) -> list:
        """Process a single chapter file and extract visual element metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract chapter number
            chapter_num = self.extract_chapter_number(file_path.stem)
            
            # Find all visual elements
            visual_elements = self.find_visual_elements(soup)
            
            logger.info(f"Found {len(visual_elements)} visual elements in {file_path.name}")
            
            metadata_list = []
            
            for visual in visual_elements:
                # Create metadata entry
                metadata = {
                    "text": visual['context_text'],
                    "metadata": {
                        "title": f"Chapter {chapter_num}",
                        "identifier": f"{isbn}_Chapter{chapter_num}",
                        "section_id": f"sec{chapter_num}",
                        "source_file": str(file_path.relative_to(self.base_dir)),
                        "asset_url": "",
                        "visuals": [
                            {
                                "type": visual['type'],
                                "image_id": visual['id'],
                                "alt_text": visual['caption']['alt_text'],
                                "figure_caption": visual['caption']['figure_caption'],
                                "source_path": visual['caption']['source_path'],
                                "copyright_info": visual['copyright_info'],
                                "tag_type": visual['tag_name'],
                                "asset_url": ""
                            }
                        ]
                    }
                }
                
                # Add table text and HTML for tables
                if visual['type'] == 'table':
                    metadata["table_all_text"] = self.extract_table_text_content(visual['element'])
                    metadata["table_html"] = self.extract_table_html(visual['element'])
                
                metadata_list.append(metadata)
            
            return metadata_list
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return []
    
    def process_single_epub(self, epub_dir: Path) -> None:
        """Process a single EPUB directory"""
        isbn = self.extract_isbn_from_path(epub_dir)
        logger.info(f"Processing EPUB: {isbn}")
        
        # Get the output directory for this ISBN
        output_dir = self.get_output_dir_for_isbn(isbn)
        logger.info(f"Output directory: {output_dir}")
        
        # Find the OEBPS or OPS directory
        content_dir = None
        for subdir in ['OEBPS', 'OPS']:
            potential_dir = epub_dir / subdir
            if potential_dir.exists():
                content_dir = potential_dir
                break
        
        if not content_dir:
            logger.warning(f"No content directory found in {epub_dir}")
            return
        
        logger.info(f"Found content directory: {content_dir}")
        
        # Find all chapter files
        chapter_files = self.find_chapter_files(content_dir)
        logger.info(f"Found {len(chapter_files)} chapter files to process")
        
        # Group metadata by chapter
        chapter_metadata = defaultdict(list)
        
        for chapter_file in chapter_files:
            logger.info(f"Processing chapter file: {chapter_file.name}")
            metadata_list = self.process_chapter_file(chapter_file, isbn, epub_dir, content_dir)
            
            # Group by chapter number
            chapter_num = self.extract_chapter_number(chapter_file.stem)
            chapter_metadata[chapter_num].extend(metadata_list)
        
        # Create JSON files for each chapter
        for chapter_num, metadata_list in chapter_metadata.items():
            if metadata_list:
                output_file = output_dir / f"Chapter{chapter_num}_visual_metadata.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_list, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Created {output_file} with {len(metadata_list)} visual element entries")
            else:
                logger.info(f"No visual elements found for Chapter {chapter_num}")
    
    def process_all_epubs(self) -> None:
        """Process all EPUBs in the base directory"""
        epub_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for epub_dir in epub_dirs:
            self.process_single_epub(epub_dir)

def main():
    """Main function to process all EPUBs"""
    # Default: Capture full paragraphs (max_sentences=None)
    extractor = BeautifulSoupImageMetadataExtractor()
    
    # Alternative: Limit to 5 sentences
    # extractor = BeautifulSoupImageMetadataExtractor(max_sentences=5)
    
    # Alternative: Limit to 3 sentences  
    # extractor = BeautifulSoupImageMetadataExtractor(max_sentences=3)
    
    logger.info("Starting EPUB visual element extraction...")
    extractor.process_all_epubs()
    logger.info("Extraction completed!")

if __name__ == "__main__":
    main() 