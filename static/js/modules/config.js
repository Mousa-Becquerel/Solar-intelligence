/**
 * Application Configuration
 *
 * Central configuration object containing all application constants.
 * Exported as named export for use across modules.
 *
 * @module config
 */

export const CONFIG = {
    // Autocomplete
    MIN_AUTOCOMPLETE_QUERY_LENGTH: 2,
    MIN_SIMILARITY_THRESHOLD: 0.3,
    AUTOCOMPLETE_BLUR_DELAY: 100,

    // Query reminders
    REMINDER_QUERY_INTERVAL: 4,
    NEWS_CARD_DISPLAY_DELAY: 10000,
    NEWS_CARD_AUTO_HIDE_DELAY: 30000,

    // Suggested queries initialization
    SUGGESTED_QUERIES_INIT_DELAY: 100,

    // Chart dimensions
    CHART_MARGIN: { top: 20, right: 20, bottom: 25, left: 80 },
    CHART_MARGIN_WITH_TITLE: 45,
    CHART_MARGIN_WITH_LEGEND: 110,
    CHART_MARGIN_WITH_LEGEND_NO_TITLE: 90,

    // Animation
    CHART_ANIMATION_DELAY_BASE: 1500,
    CHART_ANIMATION_DELAY_INCREMENT: 50,
    CHART_ANIMATION_DURATION: 300,

    // Timeouts
    SIDEBAR_AUTO_COLLAPSE_DELAY: 300
};
