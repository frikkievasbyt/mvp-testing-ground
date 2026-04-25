(() => {
  const toolbars = document.querySelectorAll('.directory-toolbar[data-target]');
  if (!toolbars.length) return;

  toolbars.forEach((toolbar) => {
    const targetSelector = toolbar.getAttribute('data-target');
    const grid = document.querySelector(targetSelector);
    if (!grid) return;

    const cards = Array.from(grid.querySelectorAll('.listing-card'));
    const textInput = toolbar.querySelector('.js-filter-text');
    const visibleCount = toolbar.querySelector('.js-visible-count');
    const totalCount = toolbar.querySelector('.js-total-count');

    const applyFilters = () => {
      const q = (textInput?.value || '').trim().toLowerCase();
      let shown = 0;

      cards.forEach((card) => {
        const name = card.dataset.name || '';
        const address = card.dataset.address || '';
        const textMatch = !q || name.includes(q) || address.includes(q);

        card.classList.toggle('hidden-by-filter', !textMatch);
        if (textMatch) shown += 1;
      });

      if (visibleCount) visibleCount.textContent = String(shown);
      if (totalCount) totalCount.textContent = String(cards.length);
    };

    textInput?.addEventListener('input', applyFilters);
    applyFilters();
  });
})();
