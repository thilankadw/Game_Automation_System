"use client";

import { useState } from "react";

import { OcrReadingsDeleteButton } from "@/components/ocr-readings-delete-button";
import { OcrRunButton } from "@/components/ocr-run-button";
import { ScreenshotDeleteButton } from "@/components/screenshot-delete-button";
import type { StoredScreenshotSession } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";

export interface ScreenshotGalleryProps {
  apiBaseUrl: string;
  gameId: number;
  gameName: string;
  sessions: StoredScreenshotSession[];
}

const INITIAL_FRAME_COUNT = 12;

/**
 * Renders persisted capture sessions as collapsible screenshot galleries.
 *
 * Only a preview strip is mounted initially so games with thousands of spins
 * do not create an excessive number of image elements.
 */
export function ScreenshotGallery({
  apiBaseUrl,
  gameId,
  gameName,
  sessions,
}: ScreenshotGalleryProps) {
  const totalFrames = sessions.reduce(
    (total, session) => total + session.screenshot_count,
    0,
  );

  return (
    <div className="screenshot-library">
      <div className="screenshot-library-toolbar">
        <p className="screenshot-library-note">
          Frames are stored on this machine.
        </p>
        <div className="screenshot-library-actions">
          <OcrRunButton
            gameId={gameId}
            gameName={gameName}
            sessions={sessions}
          />
          <ScreenshotDeleteButton
            frameCount={totalFrames}
            gameId={gameId}
            gameName={gameName}
            sessionCount={sessions.length}
          />
        </div>
      </div>
      {sessions.map((session, index) => (
        <details
          className="screenshot-session"
          key={session.id}
          open={index === 0}
        >
          <summary className="screenshot-session-summary">
            <span className="screenshot-session-main">
              <span className="screenshot-session-title">
                Session {session.id.slice(0, 8)}
              </span>
              <span className="screenshot-session-meta">
                {formatDateTime(session.created_at)} · {session.width}×
                {session.height}
              </span>
            </span>
            <span className="screenshot-session-count">
              {formatNumber(session.screenshot_count)} frames
            </span>
            <span
              aria-hidden="true"
              className="screenshot-session-chevron"
            />
          </summary>
          <SessionFrames
            apiBaseUrl={apiBaseUrl}
            gameId={gameId}
            gameName={gameName}
            session={session}
          />
        </details>
      ))}
    </div>
  );
}

interface SessionFramesProps {
  apiBaseUrl: string;
  gameId: number;
  gameName: string;
  session: StoredScreenshotSession;
}

/**
 * Renders the screenshots in one session with expand and delete controls.
 */
function SessionFrames({
  apiBaseUrl,
  gameId,
  gameName,
  session,
}: SessionFramesProps) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll
    ? session.screenshots
    : session.screenshots.slice(0, INITIAL_FRAME_COUNT);

  return (
    <>
      <div className="screenshot-strip">
        {visible.map((src, index) => (
          <a
            className="screenshot-thumb"
            href={`${apiBaseUrl}${src}`}
            key={src}
            rel="noreferrer"
            target="_blank"
          >
            {/* Screenshots are served by the API on a separate origin. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              alt={`Spin ${index + 1} of ${gameName}`}
              decoding="async"
              loading="lazy"
              src={`${apiBaseUrl}${src}`}
            />
            <span className="screenshot-thumb-index">{index + 1}</span>
          </a>
        ))}
      </div>
      <div className="screenshot-session-actions">
        {session.screenshots.length > INITIAL_FRAME_COUNT ? (
          <button
            className="button button-ghost button-sm screenshot-more"
            onClick={() => setShowAll((current) => !current)}
            type="button"
          >
            {showAll
              ? "Show fewer frames"
              : `Show all ${formatNumber(session.screenshots.length)} frames`}
          </button>
        ) : null}
        {session.ocr_reading_count > 0 ? (
          <OcrReadingsDeleteButton
            gameId={gameId}
            gameName={gameName}
            readingCount={session.ocr_reading_count}
            sessionId={session.id}
            triggerClassName="button button-ghost button-sm"
          />
        ) : null}
        <ScreenshotDeleteButton
          frameCount={session.screenshot_count}
          gameId={gameId}
          gameName={gameName}
          sessionId={session.id}
          triggerClassName="button button-ghost button-sm screenshot-session-delete"
        />
      </div>
    </>
  );
}
