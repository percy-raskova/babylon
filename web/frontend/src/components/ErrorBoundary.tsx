/**
 * React Error Boundary — catches render crashes in child components.
 *
 * Prevents a single failing component (e.g., GraphView, DeckGLMap)
 * from taking down the entire GameShell with a black screen.
 */

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Label shown in the default fallback when the boundary catches an error. */
  fallbackLabel?: string;
  /**
   * Custom fallback UI rendered instead of the default error card when a child
   * throws. Used to degrade gracefully (e.g. the Briefing map falls back to the
   * static placeholder on a WebGL/deck.gl init failure instead of white-screening
   * the route).
   */
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error(
      `[ErrorBoundary] ${this.props.fallbackLabel ?? "Component"} crashed:`,
      error,
      info.componentStack,
    );
  }

  render(): ReactNode {
    if (this.state.error) {
      if (this.props.fallback !== undefined) {
        return this.props.fallback;
      }
      return (
        <div className="flex h-full w-full items-center justify-center rounded-lg border border-wet-concrete bg-dark-metal p-4 text-center">
          <div>
            <p className="text-sm font-medium text-crimson">
              {this.props.fallbackLabel ?? "Component"} failed to render
            </p>
            <p className="mt-1 text-xs text-ash">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-3 rounded border border-wet-concrete px-3 py-1 text-xs text-silver hover:border-silver"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
