/**
 * DOM Utilities
 * Helper functions for DOM manipulation
 */

/**
 * Create element with classes and attributes
 * @param {string} tag - HTML tag name
 * @param {object} options - Options (classes, attributes, textContent, innerHTML)
 * @returns {HTMLElement}
 */
export function createElement(tag, options = {}) {
    const element = document.createElement(tag);

    if (options.classes) {
        if (Array.isArray(options.classes)) {
            // Filter out empty strings
            const validClasses = options.classes.filter(cls => cls && cls.trim());
            if (validClasses.length > 0) {
                element.classList.add(...validClasses);
            }
        } else if (options.classes && options.classes.trim()) {
            element.className = options.classes;
        }
    }

    if (options.attributes) {
        Object.entries(options.attributes).forEach(([key, value]) => {
            element.setAttribute(key, value);
        });
    }

    if (options.textContent) {
        element.textContent = options.textContent;
    }

    if (options.innerHTML) {
        element.innerHTML = options.innerHTML;
    }

    if (options.children) {
        options.children.forEach(child => {
            if (child instanceof HTMLElement) {
                element.appendChild(child);
            }
        });
    }

    return element;
}

/**
 * Show element (remove hidden class)
 * @param {HTMLElement|string} element - Element or selector
 */
export function showElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.remove('hidden');
        el.style.display = '';
    }
}

/**
 * Hide element (add hidden class)
 * @param {HTMLElement|string} element - Element or selector
 */
export function hideElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.add('hidden');
    }
}

/**
 * Toggle element visibility
 * @param {HTMLElement|string} element - Element or selector
 */
export function toggleElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.toggle('hidden');
    }
}

/**
 * Clear all children from element
 * @param {HTMLElement|string} element - Element or selector
 */
export function clearElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.innerHTML = '';
    }
}

/**
 * Scroll element to bottom
 * @param {HTMLElement|string} element - Element or selector
 * @param {boolean} smooth - Use smooth scrolling
 */
export function scrollToBottom(element, smooth = false) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        if (smooth) {
            el.scrollTo({
                top: el.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            el.scrollTop = el.scrollHeight;
        }
    }
}

/**
 * Check if element is in viewport
 * @param {HTMLElement} element - Element to check
 * @returns {boolean}
 */
export function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Debounce function
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {function}
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 * @param {function} func - Function to throttle
 * @param {number} limit - Time limit in ms
 * @returns {function}
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Generate unique ID
 * @param {string} prefix - Optional prefix
 * @returns {string}
 */
export function generateId(prefix = 'id') {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Add event listener with cleanup
 * @param {HTMLElement} element - Element to attach listener
 * @param {string} event - Event name
 * @param {function} handler - Event handler
 * @returns {function} Cleanup function
 */
export function addListener(element, event, handler) {
    element.addEventListener(event, handler);
    return () => element.removeEventListener(event, handler);
}

/**
 * Query selector with error handling
 * @param {string} selector - CSS selector
 * @param {HTMLElement} context - Context element (default: document)
 * @returns {HTMLElement|null}
 */
export function qs(selector, context = document) {
    try {
        return context.querySelector(selector);
    } catch (error) {
        console.error(`Invalid selector: ${selector}`, error);
        return null;
    }
}

/**
 * Query selector all with error handling
 * @param {string} selector - CSS selector
 * @param {HTMLElement} context - Context element (default: document)
 * @returns {Array<HTMLElement>}
 */
export function qsa(selector, context = document) {
    try {
        return Array.from(context.querySelectorAll(selector));
    } catch (error) {
        console.error(`Invalid selector: ${selector}`, error);
        return [];
    }
}
