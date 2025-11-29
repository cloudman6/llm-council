import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        all_rounds: [],
        stage2: null,
        final_result: null,
        metadata: null,
        loading: {
          multi_round: true,
          current_round: 0,
          total_models: 0,
          completed_models: 0,
          current_message: ''
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'initializing':
            // Handle initialization event
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.current_message = event.data.message || 'Initializing...';
              return { ...prev, messages };
            });
            break;

          case 'round_start':
            // Handle round start
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.current_round = event.data.round;
              lastMsg.loading.current_message = event.data.message;
              lastMsg.loading.completed_models = 0;
              return { ...prev, messages };
            });
            break;

          case 'model_response_complete':
            // Handle individual model response completion
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];

              // Initialize round if it doesn't exist
              if (!lastMsg.all_rounds[event.data.round - 1]) {
                lastMsg.all_rounds[event.data.round - 1] = {
                  round: event.data.round,
                  type: event.data.round === 1 ? 'divergent' : 'convergent',
                  responses: []
                };
              }

              // Check if model already exists in this round
              const existingModelIndex = lastMsg.all_rounds[event.data.round - 1].responses
                .findIndex(r => r.model === event.data.model);

              if (existingModelIndex === -1) {
                // Add new model response
                lastMsg.all_rounds[event.data.round - 1].responses.push({
                  model: event.data.model,
                  response: event.data.response,
                  parsed_json: event.data.parsed_json
                });
              }

              lastMsg.loading.completed_models = event.data.completed_models;
              lastMsg.loading.total_models = event.data.total_models;

              return { ...prev, messages };
            });
            break;

          case 'round_complete':
            // Handle round completion
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];

              // Update round with chairman assessment
              if (lastMsg.all_rounds[event.data.round - 1]) {
                lastMsg.all_rounds[event.data.round - 1].chairman_assessment = {
                  is_converged: event.data.is_converged,
                  convergence_score: event.data.convergence_score,
                  ...event.data.chairman_assessment
                };
              }

              lastMsg.loading.current_message = `Round ${event.data.round} completed`;

              return { ...prev, messages };
            });
            break;

          case 'complete':
            // Handle complete multi-round response
            if (event.data) {
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.all_rounds = event.data.all_rounds;
                lastMsg.stage2 = event.data.stage2;
                lastMsg.final_result = event.data.final_result;
                lastMsg.metadata = event.data.metadata;
                lastMsg.loading.multi_round = false;
                lastMsg.loading.current_message = 'Discussion completed';
                return { ...prev, messages };
              });
            }
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'stream_complete':
            // Final stream completion event
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              if (lastMsg.loading) {
                lastMsg.loading.multi_round = false;
                lastMsg.loading.current_message = 'All responses received';
              }
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            // Remove optimistic messages on error
            setCurrentConversation((prev) => ({
              ...prev,
              messages: prev.messages.slice(0, -2),
            }));
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  );
}

export default App;
