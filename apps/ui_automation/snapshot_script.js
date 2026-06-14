function __grt_snapshot__() {
    const result = [];
    const selector = [
        'button', 'input:not([type="hidden"])', 'textarea', 'select', 'a',
        '[onclick]', '[role="button"]', '[role="link"]',
        '[role="checkbox"]', '[role="radio"]', '[role="menuitem"]',
        '[role="tab"]', '[role="option"]', '[contenteditable="true"]',
        'label', 'h1', 'h2', 'h3', 'h4', 'li[role="treeitem"]'
    ].join(', ');

    const elems = document.querySelectorAll(selector);
    let idx = 1;

    elems.forEach(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        if (rect.width > 0 && rect.height > 0
            && style.display !== 'none'
            && style.visibility !== 'hidden'
            && style.opacity !== '0') {

            const text = (el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '').trim().substring(0, 100);
            result.push({
                index: idx++,
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                text: text,
                id: el.id || '',
                name: el.name || '',
                href: el.href || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                placeholder: el.placeholder || '',
                title: el.title || '',
                role: el.getAttribute('role') || ''
            });
        }
    });
    return result;
}
__grt_snapshot__();
