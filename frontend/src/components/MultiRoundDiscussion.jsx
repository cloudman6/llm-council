import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './MultiRoundDiscussion.css';

/**
 * Component to display multi-round discussion results
 */
export default function MultiRoundDiscussion({ all_rounds, final_result, metadata }) {
  const [selectedRound, setSelectedRound] = useState(0);
  const [selectedModel, setSelectedModel] = useState({});

  // Auto-select the latest round when data updates
  useEffect(() => {
    if (all_rounds && all_rounds.length > 0) {
      const latestRound = all_rounds.length - 1;
      setSelectedRound(latestRound);
      setSelectedModel(prev => ({
        ...prev,
        [latestRound]: 0
      }));
    }
  }, [all_rounds]);

  // Initialize selected model for each round
  const handleRoundChange = (roundIndex) => {
    setSelectedRound(roundIndex);
    const roundData = all_rounds[roundIndex];
    if (roundData && roundData.responses && roundData.responses.length > 0 && !selectedModel[roundIndex]) {
      setSelectedModel(prev => ({
        ...prev,
        [roundIndex]: 0
      }));
    }
  };

  // Handle empty or partial data gracefully
  if (!all_rounds || all_rounds.length === 0) {
    return (
      <div className="multi-round-discussion loading">
        <div className="loading-placeholder">
          <div className="spinner"></div>
          <span>Initializing multi-round discussion...</span>
        </div>
      </div>
    );
  }

  // Helper function to get short model name
  const getModelShortName = (model) => {
    return model.split('/')[1] || model;
  };

  return (
    <div className="multi-round-discussion">
      <div className="round-tabs">
        {all_rounds.map((round, index) => (
          <button
            key={index}
            className={`round-tab ${selectedRound === index ? 'active' : ''}`}
            onClick={() => handleRoundChange(index)}
          >
            Round {index + 1}
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
                Round {index + 1}
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
              {!round.responses || round.responses.length === 0 ? (
                <div className="no-responses">
                  <div className="spinner"></div>
                  <span>Waiting for model responses...</span>
                </div>
              ) : (
                <>
                  {round.responses.length > 1 && (
                    <div className="model-tabs">
                      {round.responses.map((response, responseIndex) => (
                        <button
                          key={responseIndex}
                          className={`model-tab ${(selectedModel[index] || 0) === responseIndex ? 'active' : ''}`}
                          onClick={() => setSelectedModel(prev => ({
                            ...prev,
                            [index]: responseIndex
                          }))}
                        >
                          {getModelShortName(response.model)}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="tab-content">
                    {round.responses.map((response, responseIndex) => (
                      <div
                        key={responseIndex}
                        className={`model-response ${(selectedModel[index] || 0) === responseIndex ? 'active' : ''}`}
                        style={{ display: (selectedModel[index] || 0) === responseIndex ? 'block' : 'none' }}
                      >
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

                              {/* Only show conflicts and suggestions for rounds 2+ */}
                              {index > 0 && response.parsed_json.conflicts && (
                                <div className="json-field">
                                  <strong>Conflicts:</strong>
                                  <ul>
                                    {response.parsed_json.conflicts.map((conflict, cIndex) => (
                                      <li key={cIndex}>{conflict}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {index > 0 && response.parsed_json.suggestions && (
                                <div className="json-field">
                                  <strong>Suggestions:</strong>
                                  <ul>
                                    {response.parsed_json.suggestions.map((suggestion, sIndex) => (
                                      <li key={sIndex}>{suggestion}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

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
                </>
              )}
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