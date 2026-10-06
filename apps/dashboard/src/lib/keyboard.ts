import type { KeyboardEvent } from "react";

/** Keep keyboard focus inside an open modal, including at browser chrome boundaries. */
export function containDialogFocus(event: KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== "Tab") return;
  const items = Array.from(
    event.currentTarget.querySelectorAll<HTMLElement>(
      'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]',
    ),
  ).filter((element) => element.getClientRects().length > 0);
  const first = items[0];
  const last = items.at(-1);
  if (!first || !last) {
    event.preventDefault();
    return;
  }
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/** Arrow keys and Home/End move between tabs and activate the selected panel. */
export function navigateTabs(event: KeyboardEvent<HTMLElement>) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const tabs = Array.from(
    event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
  );
  const index = tabs.indexOf(document.activeElement as HTMLButtonElement);
  if (index < 0) return;
  event.preventDefault();
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? tabs.length - 1
        : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) %
          tabs.length;
  tabs[next].focus();
  tabs[next].click();
}
