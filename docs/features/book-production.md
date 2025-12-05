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

### EPUB Validation & Debugging

#### When EPUB Conversion Fails on Kindle/Publishing Sites

If your EPUB shows errors when uploading to Amazon KDP, Apple Books, or other publishing platforms, or when converting to MOBI/AZW3, use **Calibre** to debug and identify the issues.

**Common EPUB Errors:**
- `Failed to find image: OEBPS/images/filename.ext` - Missing or incorrectly referenced image files
- `TOC item not found in document` - Navigation points to non-existent files
- `Invalid XHTML` - Malformed HTML/XML structure
- `Missing required metadata` - ISBN, publisher, or other required fields
- `Cover image not found` - Cover reference doesn't match actual file

#### Using Calibre for EPUB Debugging

**Step 1: Install Calibre**

```bash
# Ubuntu/Debian
sudo apt install calibre

# macOS
brew install calibre

# Windows
# Download from: https://calibre-ebook.com/download
```

**Step 2: Convert EPUB with Calibre (Validates & Shows Errors)**

```bash
# Convert EPUB to MOBI (will show validation errors)
ebook-convert book.epub book.mobi --output-profile kindle

# Convert EPUB to AZW3 (newer Kindle format)
ebook-convert book.epub book.azw3 --output-profile kindle
```

**What Calibre Checks:**
- ✓ All referenced images exist
- ✓ All TOC items point to valid files
- ✓ XHTML is well-formed
- ✓ Metadata is complete
- ✓ File structure is correct
- ✓ Kindle compatibility

**Step 3: Read Error Messages**

Calibre will output detailed errors like:
```
Failed to find image: OEBPS/images/logo_horizontal.svg
TOC item Cover [OEBPS/cover.xhtml] not found in document
```

These errors tell you exactly what's wrong with your EPUB.

**Step 4: Fix Issues in FableFlow**

Common fixes:
1. **Missing images** - Ensure all referenced images are in `output/` directory
2. **Wrong image format** - Check if EPUB references `.svg` but only `.png` exists
3. **Incorrect TOC** - Verify all TOC entries match actual XHTML files
4. **Broken image paths** - Ensure paths use `images/filename.ext` format

**Step 5: Re-generate EPUB**

After fixing issues:
```bash
# Delete old EPUB to force regeneration
rm output/book.epub

# Run book production again
fable-flow publisher process
```

#### Alternative: Online EPUB Validators

**EPUBCheck (Official Validator):**
```bash
# Install Java if needed
sudo apt install default-jre

# Download EPUBCheck
wget https://github.com/w3c/epubcheck/releases/download/v5.1.0/epubcheck-5.1.0.zip
unzip epubcheck-5.1.0.zip

# Validate EPUB
java -jar epubcheck-5.1.0/epubcheck.jar book.epub
```

**Online Validators:**
- [EPUBCheck Online](http://validator.idpf.org/) - Official IDPF validator
- [Pagina EPUB Checker](https://www.pagina.gmbh/produkte/epub-checker/) - Detailed validation

#### Kindle-Specific Issues

**Amazon KDP Upload Errors:**

If Amazon KDP rejects your EPUB:

1. **Use Kindle Previewer** (Amazon's official tool):
   - Download: https://kdp.amazon.com/en_US/help/topic/G202131170
   - Open your EPUB in Kindle Previewer
   - It will show Amazon-specific compatibility issues
   - Preview how it looks on different Kindle devices

2. **Common Kindle Issues:**
   - Cover image must be referenced correctly in metadata
   - All images should be < 5MB each
   - Total EPUB size should be < 650MB
   - Use RGB color space for images (not CMYK)
   - Avoid complex CSS that Kindle doesn't support

3. **Fix and Re-validate:**
   ```bash
   # After fixing, convert with Calibre to test
   ebook-convert book.epub book.mobi

   # Then upload to KDP
   ```

#### Publishing Platform Requirements

**Amazon Kindle (KDP):**
- Accepts EPUB 2.0 and 3.0
- Automatically converts to Kindle format
- Recommends using Kindle Previewer first

**Apple Books:**
- Requires EPUB 3.0
- Strict XHTML validation
- Use Apple Books Previewer for testing

**Google Play Books:**
- Accepts EPUB 2.0 and 3.0
- More lenient validation
- Good for testing if others fail

**Kobo:**
- Accepts EPUB 2.0 and 3.0
- Similar requirements to Kindle

#### Pro Tips

1. **Always validate before uploading** - Use Calibre or EPUBCheck
2. **Test on actual devices** - Different e-readers handle EPUBs differently
3. **Keep it simple** - Complex layouts may not work across all platforms
4. **Check images** - Ensure all images are included and properly sized
5. **Use standard fonts** - Embedded fonts can cause issues on some readers

#### FableFlow EPUB Features

FableFlow generates EPUB 3.0 with:
- ✓ Both `toc.ncx` (EPUB 2.0 compatibility) and `nav.xhtml` (EPUB 3.0)
- ✓ Proper metadata (ISBN, author, publisher, description)
- ✓ Cover image with high contrast text overlay
- ✓ Optimized for Kindle, Apple Books, and other platforms
- ✓ Validated structure and navigation

If you still encounter issues after validation, please report them on [GitHub Issues](https://github.com/suneeta-mall/fable-flow/issues) with the Calibre error output.

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
