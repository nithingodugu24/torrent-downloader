import { useEffect, useRef, type RefObject } from 'react';

let locks = 0;
let previousOverflow = '';

export function useDialog<T extends HTMLElement>(
  ref: RefObject<T>,
  open: boolean,
  onClose: () => void,
  initialFocus = 'button'
) {
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    if (locks++ === 0) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }
    ref.current?.querySelector<HTMLElement>(initialFocus)?.focus();
    const keydown = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll('[aria-modal="true"]');
      const top = dialogs[dialogs.length - 1];
      if (
        !top ||
        !ref.current ||
        !(top === ref.current || top.contains(ref.current))
      )
        return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeRef.current();
      }
      if (event.key !== 'Tab') return;
      const elements = Array.from(
        ref.current.querySelectorAll<HTMLElement>(
          'button, input, textarea, select, summary, a[href], [tabindex="0"]'
        )
      ).filter(
        (element) =>
          element.getClientRects().length > 0 && !element.matches(':disabled')
      );
      if (!elements.length) {
        event.preventDefault();
        return;
      }
      const first = elements[0],
        last = elements[elements.length - 1];
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          !ref.current.contains(document.activeElement))
      ) {
        event.preventDefault();
        last.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          !ref.current.contains(document.activeElement))
      ) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      if (--locks === 0) document.body.style.overflow = previousOverflow;
      if (
        previous?.isConnected &&
        !document.querySelector('[aria-modal="true"]')
      )
        previous.focus();
    };
  }, [open, ref, initialFocus]);
}
