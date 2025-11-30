/**
 * PDF Reader Maximize/Minimize Functionality
 * Provides fullscreen reading experience for PDF viewer
 */

(function() {
    'use strict';

    // Initialize PDF reader controls when DOM is ready
    function initializePDFReaders() {
        const pdfContainers = document.querySelectorAll('.pdf-reader-container:not([data-pdf-initialized])');

        pdfContainers.forEach(container => {
            container.setAttribute('data-pdf-initialized', 'true');
            setupPDFControls(container);
        });
    }

    function setupPDFControls(container) {
        const iframe = container.querySelector('iframe');
        const maximizeBtn = container.querySelector('.pdf-maximize-btn');
        const minimizeBtn = container.querySelector('.pdf-minimize-btn');

        if (!iframe || !maximizeBtn || !minimizeBtn) {
            console.error('PDF reader: Missing required elements');
            return;
        }

        let isMaximized = false;
        let originalStyles = {
            position: container.style.position,
            top: container.style.top,
            left: container.style.left,
            width: container.style.width,
            height: container.style.height,
            zIndex: container.style.zIndex,
            background: container.style.background,
            iframeHeight: iframe.style.height
        };

        // Maximize functionality
        maximizeBtn.addEventListener('click', () => {
            if (isMaximized) return;

            // Store original styles
            originalStyles = {
                position: container.style.position,
                top: container.style.top,
                left: container.style.left,
                width: container.style.width,
                height: container.style.height,
                zIndex: container.style.zIndex,
                background: container.style.background,
                iframeHeight: iframe.style.height
            };

            // Apply fullscreen styles
            container.style.position = 'fixed';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100vw';
            container.style.height = '100vh';
            container.style.zIndex = '9999';
            container.style.background = '#2c2c2c';
            container.style.padding = '0';
            container.style.margin = '0';

            // Make iframe fill the container (accounting for controls)
            iframe.style.height = 'calc(100vh - 50px)';
            iframe.style.margin = '0';

            // Toggle button visibility
            maximizeBtn.style.display = 'none';
            minimizeBtn.style.display = 'inline-flex';

            // Prevent body scroll
            document.body.style.overflow = 'hidden';

            isMaximized = true;
        });

        // Minimize functionality
        minimizeBtn.addEventListener('click', () => {
            if (!isMaximized) return;

            // Restore original styles
            container.style.position = originalStyles.position;
            container.style.top = originalStyles.top;
            container.style.left = originalStyles.left;
            container.style.width = originalStyles.width;
            container.style.height = originalStyles.height;
            container.style.zIndex = originalStyles.zIndex;
            container.style.background = originalStyles.background;
            container.style.padding = '';
            container.style.margin = '';

            iframe.style.height = originalStyles.iframeHeight;
            iframe.style.margin = '';

            // Toggle button visibility
            maximizeBtn.style.display = 'inline-flex';
            minimizeBtn.style.display = 'none';

            // Restore body scroll
            document.body.style.overflow = '';

            isMaximized = false;
        });

        // ESC key to minimize
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isMaximized) {
                minimizeBtn.click();
            }
        });
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePDFReaders);
    } else {
        initializePDFReaders();
    }

    // Re-initialize when content changes (for dynamic content loading)
    const observer = new MutationObserver(() => {
        initializePDFReaders();
    });

    // Start observing when DOM is ready
    if (document.body) {
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        });
    }
})();
