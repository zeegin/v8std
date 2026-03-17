(() => {
  const SEARCH_BUTTON_SELECTOR = "[data-md-component='search'] button";
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
  const OBSERVED_ATTRIBUTE_NAMES = ["aria-keyshortcuts", "title", "aria-label"];
  const MAX_ATTEMPTS = 40;
  const ATTEMPT_DELAY_MS = 75;
  const SEARCH_UI_FILTERS_SELECTOR = ".F";
  const SEARCH_UI_TAGS_SELECTOR = ".I";

  function isMacPlatform() {
    const userAgentDataPlatform = navigator.userAgentData?.platform;
    if (typeof userAgentDataPlatform === "string" && userAgentDataPlatform !== "") {
      return /mac/i.test(userAgentDataPlatform);
    }

    return /mac|iphone|ipad|ipod/i.test(navigator.platform || navigator.userAgent);
  }

  function getShortcutLabel() {
    return "/";
  }

  function getSearchPlaceholder() {
    return `Поиск по теме, коду диагностики или номеру стандарта (${getShortcutLabel()})`;
  }

  function isEditableTarget(target) {
    if (!(target instanceof HTMLElement)) {
      return false;
    }

    if (target.isContentEditable) {
      return true;
    }

    if (target instanceof HTMLTextAreaElement) {
      return !target.readOnly && !target.disabled;
    }

    if (target instanceof HTMLSelectElement) {
      return !target.disabled;
    }

    if (target instanceof HTMLInputElement) {
      const allowedTypes = new Set([
        "",
        "email",
        "number",
        "password",
        "search",
        "tel",
        "text",
        "url",
      ]);

      return allowedTypes.has(target.type) && !target.readOnly && !target.disabled;
    }

    return false;
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

  function openSearch() {
    const searchButton = document.querySelector(SEARCH_BUTTON_SELECTOR);
    if (searchButton instanceof HTMLButtonElement) {
      searchButton.click();
      waitForSearchInput((input) => {
        input.focus();
        input.select?.();
      });
      return;
    }

    const container = document.querySelector(SEARCH_CONTAINER_SELECTOR);
    if (container instanceof HTMLElement) {
      container.click();
    }

    const label = document.querySelector(SEARCH_LABEL_SELECTOR);
    if (label instanceof HTMLElement) {
      label.click();
    }

    const toggle = document.querySelector(SEARCH_TOGGLE_SELECTOR);
    if (toggle instanceof HTMLInputElement) {
      toggle.checked = true;
      toggle.dispatchEvent(new Event("change", { bubbles: true }));
      toggle.dispatchEvent(new Event("input", { bubbles: true }));
    }

    waitForSearchInput((input) => {
      input.focus();
      input.select?.();
    });
  }

  function replaceShortcutText(value) {
    if (typeof value !== "string" || value === "") {
      return value;
    }

    return value
      .replace(/\bCommand\s*\+\s*K\b/g, "/")
      .replace(/\bCommand\s+K\b/g, "/")
      .replace(/\bCmd\s*\+\s*K\b/g, "/")
      .replace(/\bCmd\s+K\b/g, "/")
      .replace(/\bCtrl\s*\+\s*K\b/g, "/")
      .replace(/\bCtrl\s+K\b/g, "/")
      .replace(/\bCtrl\s*\+\s*F\b/g, "/")
      .replace(/\bCtrl\s+F\b/g, "/")
      .replace(/⌘\s*\+\s*K/g, "/")
      .replace(/⌘\s*K/g, "/");
  }

  function syncSearchUiInput(input) {
    const nextPlaceholder = getSearchPlaceholder();
    if (input.getAttribute("placeholder") !== nextPlaceholder) {
      input.setAttribute("placeholder", nextPlaceholder);
    }

    if (input.getAttribute("aria-label") !== "Поиск по сайту") {
      input.setAttribute("aria-label", "Поиск по сайту");
    }
  }

  function syncSearchUiHeadings(root) {
    const filtersHeading = root.querySelector(SEARCH_UI_FILTERS_SELECTOR);
    if (filtersHeading instanceof HTMLElement && filtersHeading.textContent === "Filters") {
      filtersHeading.textContent = "Фильтры";
    }

    const tagsHeading = root.querySelector(SEARCH_UI_TAGS_SELECTOR);
    if (tagsHeading instanceof HTMLElement && tagsHeading.textContent === "Tags") {
      tagsHeading.textContent = "Теги";
    }
  }

  function syncSearchUi(root) {
    if (!(root instanceof Document || root instanceof ShadowRoot || root instanceof Element)) {
      return;
    }

    const inputs = [];

    if (
      root instanceof HTMLInputElement &&
      root.matches("input[role='combobox'], input[type='search'], input[name='query']")
    ) {
      inputs.push(root);
    } else {
      root
        .querySelectorAll("input[role='combobox'], input[type='search'], input[name='query']")
        .forEach((input) => {
          if (input instanceof HTMLInputElement) {
            inputs.push(input);
          }
        });
    }

    for (const input of inputs) {
      syncSearchUiInput(input);
    }

    syncSearchUiHeadings(root);
  }

  function syncTextNodes(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const textNodes = [];

    while (walker.nextNode()) {
      textNodes.push(walker.currentNode);
    }

    for (const textNode of textNodes) {
      if (!(textNode.parentElement instanceof HTMLElement)) {
        continue;
      }

      const parentTagName = textNode.parentElement.tagName;
      if (parentTagName === "SCRIPT" || parentTagName === "STYLE") {
        continue;
      }

      const nextValue = replaceShortcutText(textNode.nodeValue || "");
      if (nextValue !== textNode.nodeValue) {
        textNode.nodeValue = nextValue;
      }
    }
  }

  function syncAttributes(root) {
    if (!(root instanceof Document || root instanceof ShadowRoot || root instanceof Element)) {
      return;
    }

    for (const element of root.querySelectorAll("*")) {
      if (!(element instanceof HTMLElement)) {
        continue;
      }

      for (const attributeName of OBSERVED_ATTRIBUTE_NAMES) {
        const attributeValue = element.getAttribute(attributeName);
        if (attributeValue === null) {
          continue;
        }

        const nextValue = replaceShortcutText(attributeValue);
        if (nextValue !== attributeValue) {
          element.setAttribute(attributeName, nextValue);
        }
      }
    }
  }

  function syncShortcutLabels(root) {
    syncTextNodes(root);
    syncAttributes(root);
  }

  function observeRoot(root) {
    syncShortcutLabels(root);
    syncSearchUi(root);

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") {
          const textNode = mutation.target;
          const nextValue = replaceShortcutText(textNode.nodeValue || "");
          if (nextValue !== textNode.nodeValue) {
            textNode.nodeValue = nextValue;
          }
          continue;
        }

        if (mutation.type === "attributes" && mutation.target instanceof HTMLElement) {
          const attributeName = mutation.attributeName;
          if (attributeName && OBSERVED_ATTRIBUTE_NAMES.includes(attributeName)) {
            const attributeValue = mutation.target.getAttribute(attributeName) || "";
            const nextValue = replaceShortcutText(attributeValue);
            if (nextValue !== attributeValue) {
              mutation.target.setAttribute(attributeName, nextValue);
            }
          }
          continue;
        }

        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLElement) {
            syncShortcutLabels(node);
            syncSearchUi(node);
            if (node.shadowRoot) {
              observeRoot(node.shadowRoot);
            }
          } else if (node instanceof ShadowRoot) {
            observeRoot(node);
          } else if (node instanceof Text) {
            const nextValue = replaceShortcutText(node.nodeValue || "");
            if (nextValue !== node.nodeValue) {
              node.nodeValue = nextValue;
            }
          }
        }
      }
    });

    observer.observe(root, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: OBSERVED_ATTRIBUTE_NAMES,
    });
  }

  function bindDocumentObserver() {
    observeRoot(document);

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLElement && node.shadowRoot) {
            observeRoot(node.shadowRoot);
          }
        }
      }
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });

    for (const element of document.querySelectorAll("*")) {
      if (element instanceof HTMLElement && element.shadowRoot) {
        observeRoot(element.shadowRoot);
      }
    }
  }

  function handleShortcut(event) {
    if (event.defaultPrevented || event.altKey) {
      return;
    }

    if (isEditableTarget(event.target)) {
      return;
    }

    if (!event.metaKey && !event.ctrlKey && !event.shiftKey && event.key === "/") {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
      openSearch();
      return;
    }

    if (event.shiftKey) {
      return;
    }

    const key = event.key.toLowerCase();
    const isMac = isMacPlatform();
    const modifierPressed = isMac ? event.metaKey : event.ctrlKey;
    const shortcutKey = isMac ? "k" : "f";
    const blockedLegacyKey = isMac ? null : "k";

    if (!modifierPressed) {
      return;
    }

    if (key === shortcutKey) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
      openSearch();
      return;
    }

    if (blockedLegacyKey && key === blockedLegacyKey) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
    }
  }

  function start() {
    bindDocumentObserver();
    window.addEventListener("keydown", handleShortcut, { capture: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
