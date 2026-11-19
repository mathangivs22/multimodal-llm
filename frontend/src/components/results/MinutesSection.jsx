import { formatDay, formatRange } from "../../utils/time.js";
import { EvidenceList, Speaker, firstName } from "./Evidence.jsx";
import { useResults } from "./ResultsContext.jsx";

export default function MinutesSection() {
  const { analysis, people } = useResults();
  const { summary, participants, topics, decisions, action_items: actions } = analysis;

  return (
    <section id="minutes" className="results-section" aria-labelledby="minutes-title">
      <h2 id="minutes-title" className="section-title">Minutes</h2>

      <div className="panel">
        <h3>Summary</h3>
        <p className="overview">{summary.overview}</p>
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
        <ul className="attendees">
          {participants.map((p) => (
            <li key={p.id}>
              <Speaker id={p.id} showRole />
            </li>
          ))}
        </ul>
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
              <li key={d.id} className="decision">
                <CheckIcon />
                <div>
                  <p className="decision-text">{d.text}</p>
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
                <th scope="col">Task</th>
                <th scope="col">Owner</th>
                <th scope="col">Due</th>
                <th scope="col" className="col-source">Source</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((a) => (
                <tr key={a.id}>
                  <td className="action-task">{a.task}</td>
                  <td>{a.owner_id ? <Speaker id={a.owner_id} /> : <span className="muted">Unassigned</span>}</td>
                  <td className="action-due">
                    {a.due_date ? formatDay(a.due_date) : <span className="muted">No date</span>}
                  </td>
                  <td className="col-source">
                    <EvidenceList evidence={a.evidence} label="" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function CheckIcon() {
  return (
    <svg className="decision-icon" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="9" />
      <path d="M6 10.5l2.5 2.5L14 7.5" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
