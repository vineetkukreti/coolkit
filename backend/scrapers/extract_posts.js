() => {
    // NOTE: "see more" buttons are clicked by Python (Playwright) BEFORE this JS runs.
    // Do NOT click them here — JS clicks are async and innerText won't update in time.

    const results = [];
    const boxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');

    boxes.forEach((span) => {
        // Walk up to find post container (common ancestor with author button)
        let container = span.parentElement;
        let authorBtn = null;
        for (let i = 0; i < 15 && container; i++) {
            authorBtn = container.querySelector('button[aria-label*="Open control menu for post by"]');
            if (authorBtn) break;
            container = container.parentElement;
        }

        if (!container) return;

        const authorName = authorBtn
            ? authorBtn.getAttribute('aria-label').replace('Open control menu for post by ', '').trim()
            : '';

        // Profile link
        const profileLink = container.querySelector('a[href*="/in/"]');
        const authorUrl = profileLink ? profileLink.href.split('?')[0] : '';

        // Headline (author subtitle text)
        const headlineEl = container.querySelector(
            'span.update-components-actor__description, ' +
            'span[class*="actor__description"], ' +
            'div[class*="actor__description"]'
        );
        const headline = headlineEl ? headlineEl.innerText.trim().split('\n')[0] : '';

        // Emails — from mailto links AND regex from post text
        const emailLinks = Array.from(container.querySelectorAll('a[href]'))
            .filter(a => a.href.startsWith('mailto:'));
        const mailtoEmails = emailLinks.map(a => a.href.slice(7).split('?')[0]);

        // Also regex-extract emails from the post content text
        const emailRegex = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g;
        const contentText = span.innerText || '';
        const regexEmails = contentText.match(emailRegex) || [];

        // Deduplicate
        const allEmails = [...new Set([...mailtoEmails, ...regexEmails])];
        const emails = allEmails.join(', ');

        // Post URL
        const postLink = container.querySelector('a[href*="/posts/"], a[href*="ugcPost"], a[href*="activity"]');
        const postUrl = postLink ? postLink.href.split('?')[0] : '';

        // Date
        const timeEl = container.querySelector('time');
        const postDate = timeEl ? (timeEl.getAttribute('datetime') || timeEl.innerText).trim() : '';

        // Links — extract external links + LinkedIn shortened links (lnkd.in)
        const allLinks = Array.from(container.querySelectorAll('a[href]'))
            .map(a => a.href)
            .filter(h => h.startsWith('http'))
            .filter(h => !h.includes('linkedin.com'))  // exclude all LinkedIn internal URLs
            .filter(h => !h.startsWith('mailto:'));
        const links = [...new Set(allLinks)].join(', ');

        // Full content — after "see more" has been clicked, innerText should have everything
        const content = span.innerText.trim();
        if (content.length > 20) {
            results.push({ authorName, authorUrl, headline, emails, postUrl, postDate, content, links });
        }
    });

    return results;
}
