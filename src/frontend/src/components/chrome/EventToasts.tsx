/**
 * EventToasts — chrome stub, placeholder mount point (architecture §4.2's
 * transient toast queue for `important` events on tick advance; net-new,
 * no legacy component to host). Renders empty until Lane E wires
 * `eventsSlice`/`classifyEvents` fan-out into it.
 */

interface EventToastsProps {
  gameId: string;
}

export function EventToasts(_props: EventToastsProps): React.JSX.Element {
  return (
    <div
      data-testid="event-toasts"
      className="pointer-events-none absolute right-3 top-14 flex flex-col gap-2"
    />
  );
}
