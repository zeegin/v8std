(() => {
  const STORAGE_KEY = "v8std.announce.dismissed";
  const HIDE_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

  function getStorage() {
    try {
      return window.localStorage;
    } catch (error) {
      return null;
    }
  }

  function normalize(value) {
    return (value || "").replace(/\s+/g, " ").trim();
  }

  function buildSignature(banner) {
    const text = normalize(
      banner.querySelector("[data-v8std-announce-text]")?.textContent
    );
    const href = normalize(
      banner.querySelector("[data-v8std-announce-link]")?.href
    );
    const source = `${text}::${href}`;

    if (typeof window.__md_hash === "function") {
      return `v1:${window.__md_hash(source)}`;
    }

    return `v1:${source}`;
  }

  function clearState(storage) {
    if (!storage) {
      return;
    }

    try {
      storage.removeItem(STORAGE_KEY);
    } catch (error) {
      // Ignore storage errors and keep the banner visible.
    }
  }

  function readState(storage) {
    if (!storage) {
      return null;
    }

    try {
      const raw = storage.getItem(STORAGE_KEY);
      if (!raw) {
        return null;
      }

      const state = JSON.parse(raw);
      if (!state || typeof state !== "object") {
        throw new Error("Invalid announce state");
      }

      if (
        typeof state.signature !== "string" ||
        typeof state.expiresAt !== "number"
      ) {
        throw new Error("Invalid announce state");
      }

      return state;
    } catch (error) {
      clearState(storage);
      return null;
    }
  }

  function writeState(storage, signature) {
    if (!storage) {
      return;
    }

    try {
      storage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          signature,
          expiresAt: Date.now() + HIDE_DURATION_MS,
        })
      );
    } catch (error) {
      // Ignore storage errors and keep the banner visible.
    }
  }

  function syncBanner(root = document) {
    const host = root.querySelector("[data-md-component='announce']");
    const banner = host?.querySelector("[data-v8std-announce]");
    if (!host || !banner) {
      return;
    }

    const storage = getStorage();
    const signature = buildSignature(banner);
    const state = readState(storage);
    const hasFreshDismissal =
      state &&
      state.signature === signature &&
      state.expiresAt > Date.now();

    if (state && !hasFreshDismissal) {
      clearState(storage);
    }

    host.hidden = Boolean(hasFreshDismissal);

    const dismissButton = banner.querySelector("[data-v8std-announce-dismiss]");
    if (!dismissButton || dismissButton.dataset.v8stdAnnounceBound === "true") {
      return;
    }

    dismissButton.dataset.v8stdAnnounceBound = "true";
    dismissButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();

      if (!storage) {
        return;
      }

      writeState(storage, signature);
      host.hidden = true;
    });
  }

  function start() {
    syncBanner(document);

    if (window.document$ && typeof window.document$.subscribe === "function") {
      window.document$.subscribe((root) => {
        syncBanner(root || document);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
