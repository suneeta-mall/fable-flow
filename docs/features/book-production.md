# Book Production

FableFlow's book production feature transforms your story into professional, multi-format books ready for digital and print distribution. Using advanced layout algorithms and AI-powered formatting, it creates beautifully structured books in PDF, EPUB, and HTML formats.

## Overview

The book production pipeline creates complete books through:

* Professional layout and typography
* Contextual illustration placement
* Multi-format generation (PDF, EPUB, HTML)
* Table of contents and navigation
* Cover design and metadata

## Agent Architecture

FableFlow uses a dedicated **Book Producer Agent** that:

- Structures enhanced manuscript into book format
- Integrates illustrations from the Illustrator Agent
- Generates professional layouts for each format
- Creates covers, TOC, front matter, and back matter
- Ensures consistency across all output formats

The Book Producer works after story processing and illustration generation are complete.

## Book Formats

### 📕 PDF (Print & Digital)

**Generated using ReportLab**

- Print-ready layout with proper margins
- Bookmarks for navigation
- Page numbers and headers
- Professional typography
- High-resolution images
- Embedded fonts

**Structure:**
- Front Cover (with title overlay on illustration)
- Title Page
- Publication Information (copyright, credits)
- Table of Contents (with page numbers)
- Preface
- Story Chapters (with contextual illustrations)
- About the Author
- Index
- Back Cover

### 📗 EPUB (E-Readers)

**Generated as EPUB3 format**

- NCX navigation for e-readers
- OPF manifest for content organization
- Responsive layout for different screen sizes
- Embedded illustrations
- Chapter navigation
- Metadata for library systems

**Features:**
- E-reader optimized (Kindle, Kobo, Apple Books)
- Reflowable text
- Adjustable font sizes
- Night mode compatible
- Accessibility features

### 🌐 HTML (Web & Preview)

**Generated as responsive HTML5**

- Web-friendly, responsive design
- Browser preview capability
- Interactive navigation
- Embedded images
- Print stylesheet
- Mobile-optimized

**Use Cases:**
- Website embedding
- Online reading
- Quick preview
- Interactive storytelling

## Key Features

### Professional Book Structure

Automatically generates:

* **Front Matter** - Cover, title page, copyright, dedication, TOC
* **Body Content** - Chapters with illustrations, proper spacing
* **Back Matter** - About author, index, additional resources

### Intelligent Illustration Placement

- Contextual image placement
- Caption generation
- Proper spacing and flow
- Print and digital optimization
- Resolution handling

### Typography & Layout

- Age-appropriate font selection
- Optimal line spacing and margins
- Chapter styling and headers
- Page breaks and flow
- Professional formatting

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Download books from the Media Gallery in all three formats
5. Preview HTML version directly in browser

### Option 2: CLI - Full Publishing Pipeline

```bash
# Run complete pipeline including book production
fable-flow publisher process
```

The Book Producer Agent runs after story processing and illustration generation.

### Configuration

Book production settings in `config/default.yaml`:

```yaml
style:
  pdf:
    # Page dimensions - Common sizes: 6x9 (432x648), 8.5x11 (612x792), A4 (595x842)
    page_size: [432.0, 648.0]  # 6x9 inches (standard trade paperback)

    # Print margins (in points, 72 points = 1 inch)
    margin_top: 36.0      # 0.5 inch
    margin_bottom: 36.0   # 0.5 inch
    margin_left: 36.0     # 0.5 inch
    margin_right: 36.0    # 0.5 inch

    # Image dimensions - Scale with page size
    image_width: 288.0            # 4 inches (inline images)
    image_height: 216.0           # 3 inches
    full_page_image_width: 360.0  # 5 inches (full-page images)
    full_page_image_height: 540.0 # 7.5 inches

    # Page numbering
    page_number_position: "bottom_center"  # Options: bottom_center, bottom_right, bottom_left
    start_page_number: 1

    # Layout preferences
    use_drop_caps: true    # Decorative first letters in chapters
    justify_text: false    # Left-align (false) or justify (true)

book:
  draft_story_author: "Your Name"
  isbn_pdf: "978-0-XXXXX-XXX-X"
  isbn_epub: "978-0-XXXXX-XXX-X"
  publisher: "FableFlow Publishing"
  publisher_location: "City, Country"
  publication_year: 2024
  edition: "First Edition"
```

**Note:** Most styling (fonts, colors, spacing) is defined in `producer/fable_flow/config.py` as part of the `PDFConfig` class. These include:

- Font families (title_font, body_font, caption_font, etc.)
- Font sizes (title_font_size: 24, body_font_size: 16, etc.)
- Colors (title_color, chapter_color, body_color, etc.)
- Spacing (paragraph_space_after, line_height_multiplier, etc.)

See `producer/fable_flow/config.py:57-155` for complete PDF styling options.

## Output

The book production pipeline generates:

**In FableFlow Studio:**
- Download links for all three formats
- HTML preview in browser
- Real-time generation progress

**CLI Output Files:**
```
output/
├── book.pdf              # Print-ready PDF
├── book.epub             # E-reader compatible EPUB
├── book.md               # Markdown version for web/docs
├── formatted_book.html   # Intermediate structured HTML (for review/editing)
└── image_planner_story.txt  # Story text with image markup
```

**Additional files in the pipeline:**

- `final_story.txt` - Enhanced manuscript after editorial review
- `image_0.png`, `image_1.png`, etc. - Generated illustrations
- `narration.m4a` - Audio narration (if generated)

## Integration

Book production integrates with:

* **Story Processing** - Uses enhanced manuscript
* **Illustration Generation** - Embeds generated images
* **Website Publishing** - Books hosted on FableFlow website
* **Distribution** - Ready for e-book stores and print-on-demand

## File Implementation

- **PDF Generation**: `producer/fable_flow/pdf.py` (ReportLab-based)
- **EPUB Generation**: `producer/fable_flow/epub.py` (EPUB3 standard)
- **HTML Generation**: LLM-powered structured content
- **Book Structure**: `producer/fable_flow/book_structure.py`
- **Book Utilities**: `producer/fable_flow/book_utils.py`

## Best Practices

1. **Format Selection**
    * Generate all three formats for maximum reach
    * Use PDF for print-on-demand services
    * Use EPUB for e-book stores
    * Use HTML for website embedding

2. **Quality Control**
    * Review PDF layout before printing
    * Test EPUB on multiple e-readers
    * Check HTML responsiveness
    * Verify image quality and placement

3. **Distribution**
    * Include proper metadata (ISBN, author, copyright)
    * Test on target platforms before publishing
    * Provide multiple download options
    * Consider accessibility features

## Publishing Workflow

1. **Story Processing** → Editorial review complete
2. **Illustration Generation** → Contextual images created
3. **Book Production** → All formats generated
4. **Quality Review** → Check layouts and formatting
5. **Distribution** → Publish to website, e-book stores, print services

## Troubleshooting

### Common Issues

**Issue**: Images not appearing in PDF
**Solution**: Verify illustrations were generated and paths are correct

**Issue**: EPUB not opening on e-reader
**Solution**: Validate EPUB3 format and check metadata

**Issue**: HTML layout broken on mobile
**Solution**: Verify responsive CSS and test on multiple devices

**Issue**: Page breaks in wrong places
**Solution**: Adjust chapter structure and layout settings

### Getting Help

- Check the [complete workflow documentation](../fableflow-workflow.md)
- Review [book structure implementation](../../producer/fable_flow/book_structure.py)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions)

## Example Output

View published books created with FableFlow:

* [Curious Cassie Series](../curious-cassie/) - Complete book examples
* [The Magic of YET!](../books/curious_cassie/cassie_caleb_n_magic_of_yet/book.md) - Full book with all formats
* [Beach Ride Quest](../books/curious_cassie/curious_cassie_beach_ride_quests/book.md) - Children's educational book

---

**Book Production** is a core feature that makes FableFlow unique - transforming your story into professional, multi-format publications ready for global distribution.
