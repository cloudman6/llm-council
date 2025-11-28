import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Component to display multi-round discussion results
 */
export default function MultiRoundDiscussion({ all_rounds, stage2, final_result, metadata }) {
  const [selectedRound, setSelectedRound] = useState(0);

  if (!all_rounds || all_rounds.length === 0) {
    return null;
  }

  return (
    <div className="multi-round-discussion">
      <div className="round-tabs">
        {all_rounds.map((round, index) => (
          <button
            key={index}
            className={`round-tab ${selectedRound === index ? 'active' : ''}`}
            onClick={() => setSelectedRound(index)}
          >
            {round.type === 'divergent' ? 'Divergent Phase' : `Convergent Round ${round.round}`}
          </button>
        ))}
      </div>

      <div className="round-content">
        {all_rounds.map((round, index) => (
          <div
            key={index}
            className={`round-panel ${selectedRound === index ? 'active' : ''}`}
          >
            {/* Round Header */}
            <div className="round-header">
              <h3>
                {round.type === 'divergent' ? 'Divergent Phase' : `Convergent Round ${round.round}`}
              </h3>
              {round.chairman_assessment && (
                <div className="convergence-info">
                  <span className={`convergence-status ${round.chairman_assessment.is_converged ? 'converged' : 'not-converged'}`}>
                    {round.chairman_assessment.is_converged ? '✓ Converged' : '↻ Not Converged'}
                  </span>
                  <span className="convergence-score">
                    Convergence: {round.chairman_assessment.convergence_score}
                  </span>
                </div>
              )}
            </div>

            {/* Model Responses */}
            <div className="model-responses">
              <h4>Model Responses:</h4>
              {round.responses.map((response, responseIndex) => (
                <div key={responseIndex} className="model-response">
                  <div className="model-header">
                    <strong>{response.model}</strong>
                  </div>
                  <div className="response-content">
                    {response.parsed_json ? (
                      <div className="json-response">
                        <div className="json-field">
                          <strong>Summary:</strong> {response.parsed_json.summary}
                        </div>
                        <div className="json-field">
                          <strong>Viewpoints:</strong>
                          <ul>
                            {response.parsed_json.viewpoints.map((viewpoint, vIndex) => (
                              <li key={vIndex}>{viewpoint}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="json-field">
                          <strong>Conflicts:</strong>
                          <ul>
                            {response.parsed_json.conflicts.map((conflict, cIndex) => (
                              <li key={cIndex}>{conflict}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="json-field">
                          <strong>Suggestions:</strong>
                          <ul>
                            {response.parsed_json.suggestions.map((suggestion, sIndex) => (
                              <li key={sIndex}>{suggestion}</li>
                            ))}
                          </ul>
                        </div>
                        {response.parsed_json.final_answer_candidate && (
                          <div className="json-field">
                            <strong>Final Answer Candidate:</strong>
                            <div className="markdown-content">
                              <ReactMarkdown>{response.parsed_json.final_answer_candidate}</ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="raw-response">
                        <div className="markdown-content">
                          <ReactMarkdown>{response.response}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Chairman Assessment */}
            {round.chairman_assessment && (
              <div className="chairman-assessment">
                <h4>Chairman Assessment:</h4>
                <div className="assessment-content">
                  <div className="assessment-field">
                    <strong>Explanation:</strong> {round.chairman_assessment.explanation}
                  </div>

                  <div className="consensus-section">
                    <strong>Consensus Points:</strong>
                    <ul>
                      {round.chairman_assessment.consensus_points.map((point, pIndex) => (
                        <li key={pIndex}>{point}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="conflict-section">
                    <strong>Conflict Points:</strong>
                    <ul>
                      {round.chairman_assessment.conflict_points.map((point, pIndex) => (
                        <li key={pIndex}>{point}</li>
                      ))}
                    </ul>
                  </div>

                  {round.chairman_assessment.is_converged ? (
                    <div className="final-conclusion">
                      <strong>Final Integrated Conclusion:</strong>
                      <div className="markdown-content">
                        <ReactMarkdown>{round.chairman_assessment.final_integrated_conclusion}</ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <div className="next-round-questions">
                      <strong>Questions for Next Round:</strong>
                      <ul>
                        {round.chairman_assessment.questions_for_next_round.map((question, qIndex) => (
                          <li key={qIndex}>{question}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Final Result */}
      {final_result && (
        <div className="final-result-section">
          <h3>Final Result</h3>
          <div className="final-response">
            <div className="markdown-content">
              <ReactMarkdown>{final_result.response}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Metadata */}
      {metadata && (
        <div className="metadata-section">
          <h4>Discussion Metadata</h4>
          <div className="metadata-content">
            <div className="metadata-field">
              <strong>Converged in Round:</strong> {metadata.converged_round || 'Not converged'}
            </div>
            <div className="metadata-field">
              <strong>Total Rounds:</strong> {all_rounds.length}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}