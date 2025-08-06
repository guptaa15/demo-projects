# Image RAG Demo - AI Agent for EPUB Image Metadata Extraction

This project contains an AI agent that processes extracted EPUB files to extract meaningful image metadata and create structured JSON files for RAG (Retrieval-Augmented Generation) applications.

## Overview

The AI agent iterates through extracted EPUB directories, processes chapter files, identifies meaningful images, extracts text citations, captions, and alt-text, then generates JSON metadata files with the specified format.

## Files Structure

```
image_rag_demo/
├── README.md                           # This documentation
├── demo.py                             # Demo script showing all features
├── image_metadata_extractor.py         # Original version
├── test_image_extractor.py            # Test version for single EPUB
├── improved_image_extractor.py        # Enhanced version with better text citation extraction
├── full_image_extractor.py            # Full production version for all EPUBs
├── smart_image_filter.py              # Smart filtering version with meaningful image detection
└── IMG_Metadata/                      # Output directory organized by ISBN
    ├── 9780323697132_IMG_Metadata/    # Metadata for specific ISBN
    │   ├── Chapter022_visual_metadata.json
    │   ├── Chapter004_visual_metadata.json
    │   └── ...
    ├── 9780323498081_IMG_Metadata/    # Another ISBN
    │   ├── Chapter025_visual_metadata.json
    │   └── ...
    └── ...
```

## Features

### 1. Smart Image Filtering
- **Filters out non-meaningful images**: Icons, bullets, decorative elements, navigation buttons
- **Keeps meaningful content**: Tables, figures, diagrams, medical illustrations, educational charts
- **Multiple filtering criteria**: Filename patterns, alt-text analysis, content keywords, context analysis

### 2. Text Citation Extraction
- **Extracts meaningful text citations** that describe or reference images
- **Finds sentences** mentioning figures, images, tables, charts, diagrams
- **Context-aware**: Looks for keywords like "shows", "depicts", "illustrates", "demonstrates"

### 3. Caption and Alt-text Processing
- **Extracts figure captions** from figcaption tags
- **Processes alt-text** attributes from image tags
- **Generates visual summaries** combining multiple sources

### 4. Flexible EPUB Structure Support
- **Handles different EPUB formats**: OEBPS, OPS directories
- **Supports various chapter naming**: CHP001, B978 patterns
- **Multi-threading** for performance

### 5. Organized Output Structure
- **ISBN-based organization**: Each book gets its own directory
- **Clean file naming**: `Chapter{number}_visual_metadata.json`
- **Easy navigation**: Find metadata by ISBN and chapter

## Output Format

Each JSON file contains image metadata in the specified format:

```json
{
  "text": "Managerial decisions range from managing groups of patients at the unit level to the organization or community or health care delivery system levels (see Fig",
  "metadata": {
    "title": "Chapter 004",
    "identifier": "9780323697132_Chapter004",
    "section_id": "sec004",
    "source_file": "9780323697132/OEBPS/xhtml/CHP004.xhtml",
    "cdn_url": "https://cdn.example.com/ebooks/9780323697132/9780323697132/OEBPS/xhtml/CHP004.xhtml",
    "visuals": [
      {
        "type": "figure",
        "image_id": "chp004_gr1.jpg",
        "caption": "Fig. 4.1 The relationship between clinical and managerial decision-making.",
        "alt_text": "image",
        "cdn_url": "https://cdn.example.com/ebooks/9780323697132/images/chp004_gr1.jpg",
        "generated_visual_summary": "The relationship between clinical and managerial decision-making. Managerial decisions range from managing groups of patients at the unit level to the organization or community or health care"
      }
    ]
  }
}
```

## Usage

### 1. Run the Demo
```bash
cd image_rag_demo
python demo.py
```

### 2. Test with Single EPUB
```bash
python test_image_extractor.py
```

### 3. Test with Improved Text Citation Extraction
```bash
python improved_image_extractor.py
```

### 4. Test with Smart Filtering
```bash
python smart_image_filter.py
```

### 5. Process All EPUBs (Production)
```bash
python full_image_extractor.py
```

## Directory Structure

### Input Structure
```
extracted_epubs/
├── 9780323697132/
│   ├── OEBPS/
│   │   ├── xhtml/
│   │   │   ├── CHP001.xhtml
│   │   │   ├── CHP002.xhtml
│   │   │   └── ...
│   │   └── images/
│   └── ...
├── 9780323498081/
└── ...
```

### Output Structure
```
IMG_Metadata/
├── 9780323697132_IMG_Metadata/
│   ├── Chapter001_visual_metadata.json
│   ├── Chapter002_visual_metadata.json
│   └── ...
├── 9780323498081_IMG_Metadata/
│   ├── Chapter025_visual_metadata.json
│   └── ...
└── ...
```

## Smart Filtering Criteria

### Images Filtered Out:
- **Icons**: `icon0125_Research.jpg`, `icon01-9780323498111.jpg`
- **Decorative elements**: Borders, dividers, ornaments
- **Navigation elements**: Arrows, buttons, menu items
- **Generic alt-text**: "image", "icon", "bullet"
- **Small thumbnails**: Files with size indicators like "16x16", "32x32"

### Images Kept:
- **Tables with content**: `CHP022_tbl0001.jpg` through `CHP022_tbl0005.jpg`
- **Figures with captions**: Images with proper figure captions
- **Medical/Educational content**: Anatomical diagrams, clinical illustrations
- **Referenced images**: Images mentioned in substantial text content

## Filtering Patterns

### Non-meaningful Patterns:
```python
'icon_patterns': [
    r'icon\d*\.(jpg|png|gif|svg)',
    r'bullet', r'arrow', r'pin', r'star',
    r'check', r'cross', r'plus', r'minus',
    r'play', r'pause', r'stop', r'home',
    r'menu', r'nav', r'button', r'btn',
    r'logo', r'brand', r'decorative'
]
```

### Meaningful Keywords:
```python
'meaningful_keywords': [
    'figure', 'fig', 'table', 'chart', 'diagram', 'graph',
    'anatomy', 'physiology', 'medical', 'clinical',
    'procedure', 'technique', 'method', 'process',
    'data', 'results', 'analysis', 'comparison'
]
```

## Performance

- **Multi-threading**: Uses ThreadPoolExecutor for parallel processing
- **Error handling**: Robust error handling for individual files and EPUBs
- **Progress logging**: Detailed logging of processing progress
- **Memory efficient**: Processes files one at a time

## Requirements

- Python 3.7+
- Standard library modules: `os`, `re`, `json`, `pathlib`, `collections`, `logging`, `concurrent.futures`

## Example Results

### Before Smart Filtering:
- Chapter 006: 2 images (including icons)
- Chapter 022: 8 images (including decorative elements)
- Chapter 020: 5 images (including non-meaningful elements)

### After Smart Filtering:
- Chapter 006: 0 meaningful images (filtered out icons)
- Chapter 022: 6 meaningful images (kept tables with substantial content)
- Chapter 020: 0 meaningful images (filtered out non-meaningful elements)

## Future Enhancements

1. **Machine Learning Integration**: Use ML models to classify image types
2. **OCR Integration**: Extract text from images for better understanding
3. **Image Similarity**: Group similar images across chapters
4. **Semantic Analysis**: Use NLP to better understand image context
5. **Custom Filtering**: Allow user-defined filtering criteria

## Contributing

To extend the functionality:
1. Add new filtering patterns to `SmartImageFilter` class
2. Enhance text citation extraction in `extract_text_citation` method
3. Add new meaningful keywords to the filtering criteria
4. Implement additional output formats as needed 