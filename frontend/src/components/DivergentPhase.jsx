import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './DivergentPhase.css';

export default function DivergentPhase({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage divergent-phase">
      <h3 className="stage-title">Divergent Phase: Sequential Discussion</h3>
      <p className="stage-description">
        Models respond sequentially, each seeing all previous responses with assigned roles.
      </p>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
            <span className="role-badge">{resp.role_name}</span>
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-info">
          <div className="model-name">{responses[activeTab].model}</div>
          <div className="role-info">
            <strong>Role:</strong> {responses[activeTab].role_name}
          </div>
          <div className="role-description">
            {responses[activeTab].role_description}
          </div>
        </div>

        <div className="response-section">
          <h4>Raw Response:</h4>
          <div className="response-text markdown-content">
            <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
          </div>
        </div>

        {responses[activeTab].parsed_json && (
          <div className="parsed-json-section">
            <h4>Parsed JSON:</h4>
            <div className="json-content">
              <div className="json-field">
                <strong>Summary:</strong> {responses[activeTab].parsed_json.summary}
              </div>
              <div className="json-field">
                <strong>Viewpoints:</strong>
                <ul>
                  {responses[activeTab].parsed_json.viewpoints.map((viewpoint, idx) => (
                    <li key={idx}>{viewpoint}</li>
                  ))}
                </ul>
              </div>
              <div className="json-field">
                <strong>Conflicts:</strong>
                <ul>
                  {responses[activeTab].parsed_json.conflicts.map((conflict, idx) => (
                    <li key={idx}>{conflict}</li>
                  ))}
                </ul>
              </div>
              <div className="json-field">
                <strong>Suggestions:</strong>
                <ul>
                  {responses[activeTab].parsed_json.suggestions.map((suggestion, idx) => (
                    <li key={idx}>{suggestion}</li>
                  ))}
                </ul>
              </div>
              <div className="json-field">
                <strong>Final Answer Candidate:</strong> {responses[activeTab].parsed_json.final_answer_candidate}
              </div>
            </div>
          </div>
        )}

        {!responses[activeTab].parsed_json && (
          <div className="json-error">
            <strong>Warning:</strong> Could not parse JSON response. The model may not have followed the required format.
          </div>
        )}
      </div>
    </div>
  );
}