(() => {
  const SEARCH_CONTAINER_SELECTOR = "[data-md-component='search']";
  const SEARCH_TOGGLE_SELECTOR = "#__search";
  const SEARCH_LABEL_SELECTOR = "label[for='__search']";
  const SEARCH_INPUT_SELECTOR = [
    "input[role='combobox']",
    "[data-md-component='search-query']",
    ".md-search__input",
    "input[name='query']",
    "input[type='search']",
    "input[type='text']",
    "input:not([type])",
    "textarea",
  ].join(", ");
  const SEARCH_TRIGGER_SELECTOR = "[data-v8std-search-open], [data-v8std-search-query]";
  const MAX_ATTEMPTS = 40;
  const ATTEMPT_DELAY_MS = 75;

  function isSearchOpen() {
    const toggle = document.querySelector(SEARCH_TOGGLE_SELECTOR);
    return toggle instanceof HTMLInputElement ? toggle.checked : false;
  }

  function openSearch() {
    const container = document.querySelector(SEARCH_CONTAINER_SELECTOR);
    if (container instanceof HTMLElement) {
      container.click();
      return;
    }

    const label = document.querySelector(SEARCH_LABEL_SELECTOR);
    if (!isSearchOpen() && label instanceof HTMLElement) {
      label.click();
    }

    const toggle = document.querySelector(SEARCH_TOGGLE_SELECTOR);
    if (!isSearchOpen() && toggle instanceof HTMLInputElement) {
      toggle.checked = true;
      toggle.dispatchEvent(new Event("change", { bubbles: true }));
      toggle.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function querySearchInput(root) {
    const element = root.querySelector(SEARCH_INPUT_SELECTOR);
    if (
      element instanceof HTMLInputElement ||
      element instanceof HTMLTextAreaElement
    ) {
      return element;
    }

    return null;
  }

  function findSearchInput() {
    const directInput = querySearchInput(document);
    if (directInput) {
      return directInput;
    }

    for (const element of document.querySelectorAll("*")) {
      if (!(element instanceof HTMLElement) || !element.shadowRoot) {
        continue;
      }

      const shadowInput = querySearchInput(element.shadowRoot);
      if (shadowInput) {
        return shadowInput;
      }
    }

    return null;
  }

  function waitForSearchInput(onReady, attempt = 0) {
    const input = findSearchInput();
    if (input) {
      onReady(input);
      return;
    }

    if (attempt >= MAX_ATTEMPTS) {
      return;
    }

    window.setTimeout(() => {
      waitForSearchInput(onReady, attempt + 1);
    }, ATTEMPT_DELAY_MS);
  }

  function setInputValue(input, value) {
    const prototype =
      input instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");

    if (descriptor && typeof descriptor.set === "function") {
      descriptor.set.call(input, value);
      return;
    }

    input.value = value;
  }

  function emitSearchEvent(input, type) {
    let event = null;

    if (type === "input" && typeof InputEvent === "function") {
      event = new InputEvent(type, {
        bubbles: true,
        composed: true,
        data: input.value,
        inputType: "insertText",
      });
    } else if (type === "keyup" && typeof KeyboardEvent === "function") {
      event = new KeyboardEvent(type, {
        bubbles: true,
        composed: true,
        key: "Enter",
      });
    } else {
      event = new Event(type, { bubbles: true, composed: true });
    }

    input.dispatchEvent(event);
  }

  function populateSearch(input, query) {
    input.focus();

    if (typeof query !== "string" || query.length === 0) {
      return;
    }

    if (input.value !== "") {
      setInputValue(input, "");
      emitSearchEvent(input, "input");
    }

    setInputValue(input, query);
    emitSearchEvent(input, "input");
    emitSearchEvent(input, "change");
    emitSearchEvent(input, "search");
    emitSearchEvent(input, "keyup");
    input.setSelectionRange?.(query.length, query.length);
  }

  function bindSearchTrigger(trigger) {
    if (
      !(trigger instanceof HTMLButtonElement) ||
      trigger.dataset.v8stdSearchBound === "true"
    ) {
      return;
    }

    trigger.dataset.v8stdSearchBound = "true";
    trigger.addEventListener("click", (event) => {
      event.preventDefault();

      const query = trigger.dataset.v8stdSearchQuery || "";
      openSearch();
      waitForSearchInput((input) => {
        populateSearch(input, query);
      });
    });
  }

  function syncHomeSearch(root = document) {
    root.querySelectorAll(SEARCH_TRIGGER_SELECTOR).forEach(bindSearchTrigger);
  }

  function start() {
    syncHomeSearch(document);

    if (window.document$ && typeof window.document$.subscribe === "function") {
      window.document$.subscribe((root) => {
        syncHomeSearch(root || document);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
