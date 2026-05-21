const IMAGE_SELECTOR = [
  ".md-content img",
].join(", ");

const IMAGE_LINK_SELECTOR = [
  ".md-content a[href$='.svg']",
  ".md-content a[href$='.png']",
  ".md-content a[href$='.jpg']",
  ".md-content a[href$='.jpeg']",
  ".md-content a[href$='.webp']",
  ".md-content a[href*='.svg?']",
  ".md-content a[href*='.png?']",
  ".md-content a[href*='.jpg?']",
  ".md-content a[href*='.jpeg?']",
  ".md-content a[href*='.webp?']",
  ".md-content a[href*='.svg#']",
  ".md-content a[href*='.png#']",
  ".md-content a[href*='.jpg#']",
  ".md-content a[href*='.jpeg#']",
  ".md-content a[href*='.webp#']",
].join(", ");

const EXCLUDED_ANCESTORS = [
  "a",
  "button",
  ".image-lightbox-trigger",
  ".md-logo",
  ".md-header__button",
].join(", ");

function ensureLightboxOverlay() {
  let overlay = document.getElementById("image-lightbox-overlay");
  if (overlay) {
    return overlay;
  }

  overlay = document.createElement("dialog");
  overlay.id = "image-lightbox-overlay";
  overlay.className = "image-lightbox-overlay";
  overlay.setAttribute("aria-label", "Expanded image");

  const content = document.createElement("div");
  content.className = "image-lightbox-content";

  const closeButton = document.createElement("button");
  closeButton.className = "image-lightbox-close";
  closeButton.type = "button";
  closeButton.setAttribute("aria-label", "Close expanded image");
  closeButton.textContent = "×";

  const image = document.createElement("img");
  image.alt = "";

  content.appendChild(closeButton);
  content.appendChild(image);
  overlay.appendChild(content);
  document.body.appendChild(overlay);

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      overlay.close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && overlay.open) {
      overlay.close();
    }
  });

  closeButton.addEventListener("click", () => {
    overlay.close();
  });

  return overlay;
}

function openImageLightbox(sourceImage) {
  openImageLightboxFromUrl(
    sourceImage.currentSrc || sourceImage.src,
    sourceImage.alt || "",
  );
}

function openImageLightboxFromUrl(url, altText) {
  const overlay = ensureLightboxOverlay();
  const overlayImage = overlay.querySelector("img");
  if (!overlayImage) {
    return;
  }

  overlayImage.src = url;
  overlayImage.alt = altText;

  if (!overlay.open) {
    overlay.showModal();
  }
}

function decorateImage(image) {
  if (!(image instanceof HTMLImageElement)) {
    return;
  }

  if (image.dataset.lightboxBound === "true") {
    return;
  }

  if (image.closest(EXCLUDED_ANCESTORS)) {
    return;
  }

  const trigger = document.createElement("button");
  trigger.className = "image-lightbox-trigger";
  trigger.type = "button";
  trigger.setAttribute("aria-label", image.alt ? `Expand image: ${image.alt}` : "Expand image");

  const zoomBadge = document.createElement("span");
  zoomBadge.className = "image-lightbox-badge";
  zoomBadge.setAttribute("aria-hidden", "true");
  zoomBadge.textContent = "+";

  const parent = image.parentNode;
  if (!parent) {
    return;
  }

  parent.insertBefore(trigger, image);
  trigger.appendChild(image);
  trigger.appendChild(zoomBadge);
  image.dataset.lightboxBound = "true";

  trigger.addEventListener("click", () => {
    openImageLightbox(image);
  });
}

function handleImageLinkClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }

  const link = target.closest(IMAGE_LINK_SELECTOR);
  if (!(link instanceof HTMLAnchorElement)) {
    return;
  }

  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();
  openImageLightboxFromUrl(link.href, link.textContent.trim());
}

function initializeImageLightbox() {
  document.querySelectorAll(IMAGE_SELECTOR).forEach(decorateImage);

  if (document.body.dataset.imageLightboxLinksBound === "true") {
    return;
  }

  document.addEventListener("click", handleImageLinkClick, true);
  document.body.dataset.imageLightboxLinksBound = "true";
}

if (typeof document$ !== "undefined" && typeof document$.subscribe === "function") {
  document$.subscribe(() => {
    initializeImageLightbox();
  });
} else {
  document.addEventListener("DOMContentLoaded", initializeImageLightbox);
}
