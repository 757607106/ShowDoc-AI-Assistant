export function cycleDialogFocus(event: KeyboardEvent) {
  const dialog = event.currentTarget as HTMLElement
  const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(
    'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]',
  )).filter(element =>
    element.tabIndex >= 0 && !element.matches(':disabled') && !element.closest('[inert]') &&
    element.getClientRects().length > 0 && getComputedStyle(element).visibility === 'visible',
  )
  const first = focusable[0]
  const last = focusable.at(-1)
  if (event.shiftKey ? document.activeElement === first : document.activeElement === last) {
    event.preventDefault()
    const target = event.shiftKey ? last : first
    target?.focus()
  }
}
