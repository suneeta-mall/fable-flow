document$.subscribe(() => {
    // Initialize EPUB readers when the page loads
    document.addEventListener("DOMContentLoaded", function () {
        initializeEpubReaders();
    });

    // Also run when Material theme navigation changes
    initializeEpubReaders();
});

function initializeEpubReaders() {
    // Find all EPUB reader containers that haven't been initialized
    const epubContainers = document.querySelectorAll('.epub-reader-container:not([data-initialized])');

    epubContainers.forEach(container => {
        const epubPath = container.dataset.epubPath;
        const readerId = container.id;

        if (epubPath && readerId) {
            initializeEpubReader(readerId, epubPath);
            container.setAttribute('data-initialized', 'true');
        }
    });
}

function initializeEpubReader(containerId, epubPath) {
    try {
        // Create the EPUB book instance
        const book = ePub(epubPath);

        // Get the container element
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`EPUB container with ID ${containerId} not found`);
            return;
        }

        // Create reader area
        const readerArea = document.createElement('div');
        readerArea.id = `${containerId}-reader`;
        readerArea.style.width = '100%';
        readerArea.style.height = '600px';
        readerArea.style.border = '1px solid #ddd';
        readerArea.style.borderRadius = '8px';

        // Create controls
        const controls = document.createElement('div');
        controls.className = 'epub-controls';
        controls.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px;
            background: var(--md-default-bg-color);
            border-radius: 4px;
            border: 1px solid var(--md-default-fg-color--lightest);
        `;

        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.innerHTML = '← Previous';
        prevBtn.className = 'md-button';
        prevBtn.style.marginRight = '10px';

        // Next button  
        const nextBtn = document.createElement('button');
        nextBtn.innerHTML = 'Next →';
        nextBtn.className = 'md-button';
        nextBtn.style.marginLeft = '10px';

        // Chapter selector
        const chapterSelect = document.createElement('select');
        chapterSelect.style.cssText = `
            flex: 1;
            margin: 0 10px;
            padding: 5px;
            border: 1px solid var(--md-default-fg-color--lightest);
            border-radius: 4px;
            background: var(--md-default-bg-color);
            color: var(--md-default-fg-color);
        `;

        controls.appendChild(prevBtn);
        controls.appendChild(chapterSelect);
        controls.appendChild(nextBtn);

        // Clear container and add elements
        container.innerHTML = '';
        container.appendChild(controls);
        container.appendChild(readerArea);

        // Render the book
        const rendition = book.renderTo(readerArea.id, {
            width: '100%',
            height: '100%',
            flow: 'paginated'
        });

        // Display the first chapter
        const displayed = rendition.display();

        // Navigation event handlers
        prevBtn.onclick = () => rendition.prev();
        nextBtn.onclick = () => rendition.next();

        // Load table of contents
        book.loaded.navigation.then(function (nav) {
            nav.forEach(function (chapter, index) {
                const option = document.createElement('option');
                option.value = chapter.href;
                option.textContent = chapter.label;
                chapterSelect.appendChild(option);
            });
        });

        // Chapter selector change handler
        chapterSelect.onchange = function () {
            if (this.value) {
                rendition.display(this.value);
            }
        };

        // Update chapter selector when user navigates
        rendition.on('relocated', function (location) {
            const currentChapter = book.navigation.get(location.start.cfi);
            if (currentChapter) {
                chapterSelect.value = currentChapter.href;
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', function (e) {
            if (e.target.closest(`#${containerId}`)) {
                if (e.key === 'ArrowLeft') {
                    rendition.prev();
                    e.preventDefault();
                } else if (e.key === 'ArrowRight') {
                    rendition.next();
                    e.preventDefault();
                }
            }
        });

        // Store book instance for potential future use
        container._epubBook = book;
        container._epubRendition = rendition;

        console.log(`EPUB reader initialized for ${epubPath}`);

    } catch (error) {
        console.error(`Failed to initialize EPUB reader for ${epubPath}:`, error);

        // Show fallback
        const fallback = document.createElement('div');
        fallback.innerHTML = `
            <div style="padding: 20px; background-color: #f8f9fa; text-align: center; border-radius: 8px; border: 1px solid #ddd;">
                <p>📚 EPUB reader could not be loaded.</p>
                <a href="${epubPath}" download class="md-button md-button--primary">📥 Download EPUB</a>
            </div>
        `;
        container.innerHTML = '';
        container.appendChild(fallback);
    }
}