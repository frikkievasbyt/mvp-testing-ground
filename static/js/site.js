(() => {
  const toolbars = document.querySelectorAll('.directory-toolbar[data-target]');
  if (!toolbars.length) return;

  toolbars.forEach((toolbar) => {
    const targetSelector = toolbar.getAttribute('data-target');
    const grid = document.querySelector(targetSelector);
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll('.listing-card'));
    const textInput = toolbar.querySelector('.js-filter-text');
    const statusSelect = toolbar.querySelector('.js-filter-status');
    const confidenceSelect = toolbar.querySelector('.js-filter-confidence');
    const visibleCount = toolbar.querySelector('.js-visible-count');
    const totalCount = toolbar.querySelector('.js-total-count');

    const applyFilters = () => {
      const q = (textInput?.value || '').trim().toLowerCase();
      const status = statusSelect?.value || 'all';
      const confidence = confidenceSelect?.value || 'all';

      let shown = 0;

      cards.forEach((card) => {
        const name = card.dataset.name || '';
        const address = card.dataset.address || '';
        const cardStatus = card.dataset.status || 'review';
        const cardConfidence = card.dataset.confidence || 'unknown';

        const textMatch = !q || name.includes(q) || address.includes(q);
        const statusMatch = status === 'all' || cardStatus === status;
        const confidenceMatch = confidence === 'all' || cardConfidence === confidence;

        const visible = textMatch && statusMatch && confidenceMatch;
        card.classList.toggle('hidden-by-filter', !visible);
        if (visible) shown += 1;
      });

      if (visibleCount) visibleCount.textContent = String(shown);
      if (totalCount) totalCount.textContent = String(cards.length);
    };

    textInput?.addEventListener('input', applyFilters);
    statusSelect?.addEventListener('change', applyFilters);
    confidenceSelect?.addEventListener('change', applyFilters);
    applyFilters();
  });
})();
