// Navigation and UI interactions
export function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.section-content');
    const pageTitle = document.getElementById('page-title');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            
            // Update styling
            navButtons.forEach(b => {
                b.classList.remove('border-blue-500', 'text-blue-400', 'bg-slate-800');
                b.classList.add('border-transparent', 'text-slate-300');
            });
            btn.classList.remove('border-transparent', 'text-slate-300');
            btn.classList.add('border-blue-500', 'text-blue-400', 'bg-slate-800');
            
            // Update Title
            pageTitle.textContent = btn.textContent.trim();

            // Show section
            sections.forEach(sec => {
                if (sec.id === targetId) {
                    sec.classList.add('active');
                } else {
                    sec.classList.remove('active');
                }
            });

            // Trigger chart render if switching to explain
            if (targetId === 'explain' && window.shapData) {
                window.renderChart(); // Global function defined in analysis
            }
        });
    });

    // Make 'upload' the default tab automatically, or follow the URL hash
    const initialHash = window.location.hash.replace('#', '') || 'upload';
    const targetBtn = Array.from(navButtons).find(btn => btn.getAttribute('data-target') === initialHash);
    if (targetBtn) {
        targetBtn.click();
    }
}

export function initThemeToggle() {
    const htmlEl = document.documentElement;
    document.getElementById('theme-toggle').addEventListener('click', () => {
        if (htmlEl.classList.contains('dark')) {
            htmlEl.classList.remove('dark');
            localStorage.theme = 'light';
        } else {
            htmlEl.classList.add('dark');
            localStorage.theme = 'dark';
        }
    });

    // Check system/local pref initially
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        htmlEl.classList.add('dark');
    }
}
