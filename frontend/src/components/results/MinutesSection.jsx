import { formatDay, formatRange } from "../../utils/time.js";
import { ActionCheckbox, CalendarButton, resultsUrl } from "../ActionItemControls.jsx";
import { EvidenceList, Speaker, firstName } from "./Evidence.jsx";
import { useResults } from "./ResultsContext.jsx";

export default function MinutesSection() {
  const { analysis, people, missing, onActionStatus } = useResults();
  const canTick = actionsCanUpdate(analysis.action_items);
  const { summary, participants, topics, decisions, action_items: actions } = analysis;

  if (missing.has("minutes")) {
    return (
      <section id="minutes" className="results-section" aria-labelledby="minutes-title">
        <h2 id="minutes-title" className="section-title">Minutes</h2>
        <div className="panel">
          <p className="muted">Minutes weren't generated for this meeting.</p>
        </div>
      </section>
    );
  }

  return (
    <section id="minutes" className="results-section" aria-labelledby="minutes-title">
      <h2 id="minutes-title" className="section-title">Minutes</h2>

      <div className="panel">
        <h3>Summary</h3>
        {summary.overview && <p className="overview">{summary.overview}</p>}
        {summary.key_points.length > 0 && (
          <ul className="key-points">
            {summary.key_points.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h3>Attendees</h3>
        {participants.length === 0 ? (
          <p className="muted">No attendees were identified.</p>
        ) : (
          <ul className="attendees">
            {participants.map((p) => (
              <li key={p.id}>
                <Speaker id={p.id} showRole />
              </li>
            ))}
          </ul>
        )}
      </div>

      {topics.length > 0 && (
        <div className="panel">
          <h3>Topics discussed</h3>
          <ol className="topics">
            {topics.map((t) => (
              <li key={t.id} className="topic">
                <span className="topic-time">{formatRange(t.start, t.end)}</span>
                <div className="topic-body">
                  <p className="topic-title">{t.title}</p>
                  <p>{t.summary}</p>
                  <EvidenceList evidence={t.evidence} />
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="panel">
        <h3>Decisions</h3>
        {decisions.length === 0 ? (
          <p className="muted">No decisions were recorded.</p>
        ) : (
          <ul className="decisions">
            {decisions.map((d) => (
              <li key={d.id} className={`decision ${d.status === "suggested" ? "decision-suggested" : ""}`}>
                {d.status === "suggested" ? <SuggestedIcon /> : <CheckIcon />}
                <div>
                  <p className="decision-text">
                    {d.text}
                    {d.status === "suggested" && (
                      <span className="tag tag-suggested" title="Proposed in the meeting, but not clearly agreed">
                        Suggested
                      </span>
                    )}
                  </p>
                  {d.decided_by.length > 0 && (
                    <p className="decision-by">
                      Agreed by {d.decided_by.map((id) => firstName(people[id])).join(", ")}
                    </p>
                  )}
                  <EvidenceList evidence={d.evidence} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="panel">
        <h3>Action items</h3>
        {actions.length === 0 ? (
          <p className="muted">No action items were recorded.</p>
        ) : (
          <table className="data-table actions-table">
            <thead>
              <tr>
                {canTick && <th scope="col" className="col-check"><span className="visually-hidden">Done</span></th>}
                <th scope="col">Task</th>
                <th scope="col">Owner</th>
                <th scope="col">Due</th>
                <th scope="col" className="col-source">Source</th>
                <th scope="col" className="col-cal"><span className="visually-hidden">Calendar</span></th>
              </tr>
            </thead>
            <tbody>
              {actions.map((a) => (
                <tr key={a.id} className={a.status === "done" ? "action-done" : undefined}>
                  {canTick && (
                    <td className="col-check">
                      {a.can_update && (
                        <ActionCheckbox itemId={a.id} task={a.task} status={a.status}
                          onChange={(s) => onActionStatus(a.id, s)} />
                      )}
                    </td>
                  )}
                  <td className="action-task">
                    {a.task}
                    {a.status === "done" && <span className="tag tag-resolved">Done</span>}
                  </td>
                  <td>{a.owner_id ? <Speaker id={a.owner_id} /> : <span className="muted">Unassigned</span>}</td>
                  <td className="action-due">
                    {a.due_date ? formatDay(a.due_date) : a.due_text ?? <span className="muted">No date</span>}
                  </td>
                  <td className="col-source">
                    <EvidenceList evidence={a.evidence} label="" />
                  </td>
                  <td className="col-cal">
                    <CalendarButton item={{
                      id: a.id, task: a.task, dueDate: a.due_date,
                      owner: (a.owner_id && people[a.owner_id]?.name) || null,
                      meetingTitle: analysis.title, url: resultsUrl(analysis.meeting_id),
                    }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {(analysis.pending_items.length > 0 || analysis.next_meeting) && (
        <div className="panel">
          {analysis.pending_items.length > 0 && (
            <>
              <h3>Still pending</h3>
              <ul className="key-points">
                {analysis.pending_items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </>
          )}
          {analysis.next_meeting && (
            <p>
              <strong>Next meeting:</strong> {analysis.next_meeting}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/** Hollow circle: proposed, not (yet) agreed. */
function SuggestedIcon() {
  return (
    <svg className="decision-icon decision-icon-suggested" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="8.25" fill="none" strokeWidth="1.5" strokeDasharray="3 2.4" />
    </svg>
  );
}

/** Only results read from the database can be ticked (JSON-file results have no saved ids). */
function actionsCanUpdate(items) {
  return items.some((a) => a.can_update);
}

function CheckIcon() {
  return (
    <svg className="decision-icon" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="9" />
      <path d="M6 10.5l2.5 2.5L14 7.5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
