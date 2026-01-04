import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Bot, User } from 'lucide-react';
import { clsx } from 'clsx';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface Props {
    workflowId: string;
    initialHistory: ChatMessage[];
    userRequest?: string;
    finalOutput?: any;
    status: string;
    clarificationQuestions?: any[]; // Allow any to handle potential object structure from LLM
    onFeedbackSubmit?: () => void;
}

export const ChatInterface: React.FC<Props> = ({ workflowId, initialHistory, userRequest, finalOutput, status, clarificationQuestions, onFeedbackSubmit }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [pendingMessage, setPendingMessage] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const prevMessagesLength = useRef(0);

    // Sync messages with props (Source of Truth)
    useEffect(() => {
        const msgs: ChatMessage[] = [];

        // 1. User Request
        if (userRequest) msgs.push({ role: 'user', content: userRequest });

        // 3. History
        // We now rely on the backend to append the Final Output to the history chronologically.
        const allMessages = [...msgs, ...initialHistory];

        // 4. Clarification Questions
        // Logic removed: We now rely on the backend to persist clarification questions to 'initialHistory'.
        // This prevents double-rendering (one from history, one from active state).

        // Update only if changed
        if (JSON.stringify(allMessages) !== JSON.stringify(messages)) {
            setMessages(allMessages);
        }
    }, [initialHistory, userRequest, finalOutput, status, clarificationQuestions]); // Added clarificationQuestions

    // Scroll effect
    useEffect(() => {
        if (scrollRef.current) {
            // Scroll if length increases OR if we just added a pending message
            const totalCount = messages.length + (pendingMessage ? 1 : 0);
            if (totalCount > prevMessagesLength.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                prevMessagesLength.current = totalCount;
            }
        }
    }, [messages, pendingMessage]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const content = input;
        setInput('');
        setPendingMessage(content); // Show optimistic
        setLoading(true);

        try {
            if (status === 'awaiting_clarification') {
                console.log("Submitting feedback for workflow:", workflowId);
                const payload = {
                    responses: { clarification: content },
                };
                console.log("Payload:", payload);

                // Submit as Feedback
                await axios.post(`http://localhost:8000/api/workflows/${workflowId}/feedback`, payload);
                // Trigger refresh immediately
                if (onFeedbackSubmit) onFeedbackSubmit();

                // We don't get 'history' back from feedback endpoint usually, 
                // so we rely on parent polling or the callback.
                // Optimistic update will clear when polling updates status.

            } else {
                // Normal Chat
                const res = await axios.post(`http://localhost:8000/api/workflows/${workflowId}/chat`, {
                    message: content
                });
                setMessages(res.data.history);
            }
        } catch (error) {
            console.error("Chat error", error);
            // Handle error visually if needed
        } finally {
            setPendingMessage(null); // Clear pending
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-[calc(100vh-12rem)]">
            {/* Header Removed for ChatGPT style cleanliness, or keep minimal? Let's keep it minimal or remove. 
                User said "same as chatGPT", usually just messages. */}

            <div className="flex-1 overflow-y-auto p-6 space-y-6" ref={scrollRef}>
                {messages.length === 0 && !pendingMessage && status === 'started' && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center animate-pulse">
                            <Bot className="w-4 h-4" />
                        </div>
                        <div className="text-gray-500 text-sm py-2">Agent is thinking...</div>
                    </div>
                )}

                {/* Render History Messages */}
                {messages.map((msg, idx) => (
                    <div key={idx} className={clsx("flex gap-4 max-w-5xl mx-auto w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
                        {msg.role !== 'user' && (
                            <div className="w-8 h-8 rounded-full bg-green-600 text-white flex items-center justify-center shrink-0 mt-1">
                                <Bot className="w-5 h-5" />
                            </div>
                        )}

                        <div className={clsx(
                            "p-4 rounded-2xl max-w-[85%]", // Constrain width
                            msg.role === 'user'
                                ? "bg-gray-100 text-gray-800 rounded-tr-sm" // User style
                                : "prose prose-slate max-w-none bg-transparent p-0" // Assistant (Report) style
                        )}>
                            {msg.role === 'user' ? msg.content : <div className="markdown-body"><ReactMarkdown>{msg.content}</ReactMarkdown></div>}
                        </div>

                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-gray-500 text-white flex items-center justify-center shrink-0 mt-1">
                                <User className="w-5 h-5" />
                            </div>
                        )}
                    </div>
                ))}

                {/* Render Pending Message (Optimistic) */}
                {pendingMessage && (
                    <div className="flex gap-4 max-w-5xl mx-auto w-full justify-end opacity-70">
                        <div className="bg-gray-100 text-gray-800 p-4 rounded-2xl rounded-tr-sm max-w-[85%]">
                            {pendingMessage}
                        </div>
                        <div className="w-8 h-8 rounded-full bg-gray-500 text-white flex items-center justify-center shrink-0 mt-1">
                            <User className="w-5 h-5" />
                        </div>
                    </div>
                )}

                {loading && !pendingMessage && (
                    /* If loading but no pending message (unlikely in this flow but possible if system is thinking) */
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center">
                            <Bot className="w-4 h-4" />
                        </div>
                        <div className="bg-white border border-gray-200 p-3 rounded-lg rounded-tl-none">
                            <div className="flex gap-1">
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></span>
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <form onSubmit={handleSend} className="p-4 border-t border-gray-100 flex gap-2 bg-white rounded-b-xl">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={status === 'awaiting_clarification' ? "Type your answer here..." : "Ask a follow-up question..."}
                    disabled={loading}
                    className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                />
                <button
                    type="submit"
                    disabled={!input.trim() || loading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <Send className="w-5 h-5" />
                </button>
            </form>
        </div>
    );
};
