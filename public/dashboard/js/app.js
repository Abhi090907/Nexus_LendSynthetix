// Main entry point coordinating modules
import { initNavigation, initThemeToggle } from './modules/ui.js';
import { initUpload } from './modules/upload.js';
import { initAnalysis } from './modules/analysis.js';
import { initWarRoom } from './modules/war_room.js';
import { initAgent } from './modules/agent.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI features
    initNavigation();
    initThemeToggle();

    // Initialize core business logic modules
    initUpload();
    initAnalysis();
    initWarRoom();
    initAgent();
});
