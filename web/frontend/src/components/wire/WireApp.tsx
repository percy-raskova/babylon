/**
 * WireApp - main shell for The Wire 4-tab window.
 * Spec 094: ports wire-app.jsx as fresh TypeScript.
 *
 * Tabs: WIRE (triptych), INDEX, PATTERNS, CORPUS.
 * Fed by useWire hook polling GET /api/games/:id/wire/.
 */

import { useState } from "react";
import { useWire } from "@/hooks/useWire";
import { WireWindow } from "./WireWindow";
import type { WireTab } from "./WireWindow";
import { ContinentalColumn } from "./ContinentalColumn";
import { LiberatedColumn } from "./LiberatedColumn";
import { IntelColumn } from "./IntelColumn";
import { TranslationFooter } from "./TranslationFooter";
import { IndexPage } from "./IndexPage";
import { PatternsPage } from "./PatternsPage";
import { CorpusPage } from "./CorpusPage";

interface Props {
  gameId: string;
}

export function WireApp({ gameId }: Props) {
  const { data: feed, loading, error } = useWire(gameId);
  const [tab, setTab] = useState<string>("wire");
  const [activeEuph, setActiveEuph] = useState<string | null>(null);
  const [activeSup, setActiveSup] = useState<number | null>(null);
  const [euphAlways, setEuphAlways] = useState(false);

  const meta = feed.meta;
  const euphs = feed.euphemisms;
  const story = feed.story;

  const goToWire = (_storyId: string) => {
    setTab("wire");
  };

  const tabs: WireTab[] = [
    { id: "wire", label: "The Wire", count: 3, dot: "var(--babylon-spire)" },
    { id: "index", label: "Wire Index", count: feed.index.length },
    {
      id: "patterns",
      label: "Patterns",
      count: Object.keys(euphs).length,
      dot: "var(--babylon-laser)",
    },
    { id: "corpus", label: "Corpus" },
  ];

  const badge = (
    <>
      <span className="wire-label">TICK</span>
      <span
        className="text-[16px] font-bold"
        style={{
          fontFamily: "var(--font-mono)",
          color: "var(--babylon-spire)",
          textShadow: "0 0 10px rgba(77,217,230,0.4)",
          letterSpacing: "0.04em",
        }}
      >
        {String(meta.tick).padStart(4, "0")}
      </span>
      <span style={{ width: 1, height: 16, background: "var(--babylon-rebar)", margin: "0 8px" }} />
      <span
        className="text-[9px]"
        style={{
          fontFamily: "var(--font-mono)",
          color: "var(--babylon-fog)",
          letterSpacing: "0.16em",
        }}
      >
        OP - {meta.operator}
      </span>
    </>
  );

  return (
    <WireWindow tabs={tabs} activeId={tab} onTab={setTab} badge={badge}>
      {loading && (
        <div
          className="flex h-full items-center justify-center text-sm"
          style={{ color: "var(--babylon-ash)" }}
        >
          Loading wire feed...
        </div>
      )}
      {error && (
        <div
          className="flex h-full items-center justify-center text-sm"
          style={{ color: "var(--babylon-laser)" }}
        >
          Error: {error}
        </div>
      )}
      {!loading && !error && (
        <>
          {tab === "wire" && (
            <div className={`flex h-full flex-col ${euphAlways ? "euph-always" : ""}`}>
              {/* Story chrome */}
              <div
                className="flex shrink-0 items-center justify-between border-b px-4 py-2"
                style={{
                  borderColor: "var(--babylon-rebar)",
                  background: "rgba(255,255,255,0.012)",
                }}
              >
                <div className="flex items-baseline gap-3 min-w-0">
                  <span className="wire-label">STORY</span>
                  <span
                    className="text-[11px]"
                    style={{
                      color: "var(--babylon-spire)",
                      fontFamily: "var(--font-mono)",
                      letterSpacing: "0.12em",
                    }}
                  >
                    {story?.id ?? "none"}
                  </span>
                </div>
                <span
                  className="text-[9px]"
                  style={{
                    color: "var(--babylon-fog)",
                    fontFamily: "var(--font-mono)",
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                  }}
                >
                  neutrality is hegemony
                </span>
              </div>

              {/* Triptych */}
              <div className="flex min-h-0 flex-1 overflow-hidden">
                <ContinentalColumn
                  story={story}
                  activeEuph={activeEuph}
                  setActiveEuph={setActiveEuph}
                  activeSup={activeSup}
                  setActiveSup={setActiveSup}
                  euphAlways={euphAlways}
                />
                <div className="drift" />
                <LiberatedColumn
                  story={story}
                  activeEuph={activeEuph}
                  setActiveEuph={setActiveEuph}
                  euphAlways={euphAlways}
                />
                <div className="drift" />
                <IntelColumn story={story} />
              </div>

              <TranslationFooter
                activeEuph={activeEuph}
                setActiveEuph={setActiveEuph}
                euphAlways={euphAlways}
                setEuphAlways={setEuphAlways}
                euphemisms={euphs}
                filters={feed.filters}
                onOpenPatterns={() => setTab("patterns")}
              />
            </div>
          )}
          {tab === "index" && (
            <IndexPage index={feed.index} activeId={story?.id ?? null} onOpen={goToWire} />
          )}
          {tab === "patterns" && (
            <PatternsPage euphemisms={euphs} filters={feed.filters} story={story} />
          )}
          {tab === "corpus" && <CorpusPage story={story} />}
        </>
      )}
    </WireWindow>
  );
}
