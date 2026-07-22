(() => {
  function normalize(value) {
    return value
      .toLocaleLowerCase("ru-RU")
      .replace(/ё/g, "е")
      .trim()
      .replace(/^#(?=std\d)/, "");
  }

  function initialize(root) {
    if (!(root instanceof HTMLElement) || root.dataset.initialized === "true") return;
    root.dataset.initialized = "true";

    const search = root.querySelector("[data-diagnostics-search]");
    const showEmpty = root.querySelector("[data-show-empty]");
    const standards = Array.from(root.querySelectorAll("[data-standard]"));
    if (!(search instanceof HTMLInputElement) || !(showEmpty instanceof HTMLInputElement)) return;

    const initialOpen = new Map(standards.map((standard) => [standard, standard.open]));

    function filter() {
      const query = normalize(search.value);
      for (const standard of standards) {
        const clauses = Array.from(standard.querySelectorAll("[data-clause]"));
        let visibleClauses = 0;
        for (const clause of clauses) {
          const empty = clause.matches('[data-empty="true"]');
          const searchable = normalize(clause.dataset.search || "");
          const visible = (!empty || showEmpty.checked) && (!query || searchable.includes(query));
          clause.hidden = !visible;
          if (visible) visibleClauses += 1;
        }

        const standardMatches = normalize(standard.dataset.search || "").includes(query);
        const emptyStandard = standard.matches('[data-empty="true"]');
        standard.hidden =
          (emptyStandard && !showEmpty.checked) ||
          (Boolean(query) && !standardMatches && visibleClauses === 0);
        if (query && !standard.hidden) standard.open = true;
        if (!query) standard.open = initialOpen.get(standard) || false;
      }
    }

    search.addEventListener("input", filter);
    showEmpty.addEventListener("change", filter);
    filter();
  }

  function initializeAll() {
    document.querySelectorAll("[data-diagnostics-registry]").forEach(initialize);
  }

  document.addEventListener("DOMContentLoaded", initializeAll);
  if (typeof document$ !== "undefined") document$.subscribe(initializeAll);
  initializeAll();
})();
