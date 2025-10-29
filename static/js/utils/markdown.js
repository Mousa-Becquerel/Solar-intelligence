/**
 * Markdown Utilities
 * Safe markdown rendering with DOMPurify sanitization
 */

/**
 * Safely render markdown to HTML
 * @param {string} markdownText - Markdown text to render
 * @returns {string} Sanitized HTML
 */
export function safeRenderMarkdown(markdownText) {
    if (!markdownText || typeof markdownText !== 'string') {
        return '';
    }

    try {
        const rendered = marked.parse(markdownText, {
            breaks: true,
            gfm: true
        });

        return DOMPurify.sanitize(rendered, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img', 'table',
                'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'div', 'span'],
            ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'target', 'rel']
        });
    } catch (error) {
        console.error('Error rendering markdown:', error);
        return markdownText;
    }
}

/**
 * Extract plain text from markdown (strip formatting)
 * @param {string} markdownText - Markdown text
 * @returns {string} Plain text
 */
export function markdownToPlainText(markdownText) {
    if (!markdownText) return '';

    // Remove markdown syntax
    return markdownText
        .replace(/#{1,6}\s/g, '') // Headers
        .replace(/\*\*(.+?)\*\*/g, '$1') // Bold
        .replace(/\*(.+?)\*/g, '$1') // Italic
        .replace(/\[(.+?)\]\(.+?\)/g, '$1') // Links
        .replace(/`(.+?)`/g, '$1') // Inline code
        .replace(/```[\s\S]*?```/g, '') // Code blocks
        .replace(/>\s/g, '') // Blockquotes
        .replace(/[-*+]\s/g, '') // Lists
        .trim();
}
