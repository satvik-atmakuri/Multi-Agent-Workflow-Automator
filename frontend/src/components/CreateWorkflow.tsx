import { useState } from 'react';
import axios from 'axios';
import { Send, Loader2 } from 'lucide-react';
import { twMerge } from 'tailwind-merge';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

interface CreateWorkflowProps {
    onWorkflowCreated: (id: string) => void;
}

export function CreateWorkflow({ onWorkflowCreated }: CreateWorkflowProps) {
    const [request, setRequest] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!request.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/workflows/`, {
                text: request
            });
            onWorkflowCreated(response.data.workflow_id);
            setRequest('');
        } catch (err) {
            setError('Failed to create workflow. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Start New Workflow</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="request" className="block text-sm font-medium text-gray-700 mb-2">
                        What would you like the agents to do?
                    </label>
                    <textarea
                        id="request"
                        value={request}
                        onChange={(e) => setRequest(e.target.value)}
                        placeholder="e.g. Plan a 3-day trip to Tokyo for $1500..."
                        className="w-full h-32 p-4 text-gray-700 bg-gray-50 rounded-lg border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all resize-none"
                    />
                </div>

                {error && (
                    <div className="text-red-500 text-sm bg-red-50 p-3 rounded-md">
                        {error}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading || !request.trim()}
                    className={twMerge(
                        "flex items-center justify-center w-full py-3 px-6 rounded-lg text-white font-medium transition-all",
                        loading || !request.trim()
                            ? "bg-gray-300 cursor-not-allowed"
                            : "bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg"
                    )}
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                            Starting Agents...
                        </>
                    ) : (
                        <>
                            <Send className="w-5 h-5 mr-2" />
                            Launch Workflow
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
