import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { History, Activity, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';

interface WorkflowSummary {
    workflow_id: string;
    status: string;
    user_request: string; // Note: Frontend might need to derive this from state if API doesn't send top-level, 
    // but our new API sends full state in `state`
    state: {
        user_request: string;
    };
    created_at: string;
}

interface Props {
    currentWorkflowId: string | null;
    onSelectWorkflow: (id: string) => void;
}

export const Sidebar: React.FC<Props> = ({ currentWorkflowId, onSelectWorkflow }) => {
    const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHistory();
        const interval = setInterval(fetchHistory, 10000); // Poll history occasionally
        return () => clearInterval(interval);
    }, []);

    const fetchHistory = async () => {
        try {
            const res = await axios.get('http://localhost:8000/api/workflows/');
            setWorkflows(res.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch history", error);
            setLoading(false);
        }
    };

    const deleteWorkflow = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation(); // Prevent triggering onSelect
        if (!confirm("Are you sure you want to delete this chat? This cannot be undone.")) return;

        try {
            await axios.delete(`http://localhost:8000/api/workflows/${id}`);
            // Optimistic update
            setWorkflows(prev => prev.filter(w => w.workflow_id !== id));
            // If deleting current, reset
            if (currentWorkflowId === id) {
                onSelectWorkflow('');
            }
        } catch (error) {
            console.error("Failed to delete workflow", error);
            alert("Failed to delete workflow");
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
            case 'failed': return <XCircle className="w-4 h-4 text-red-500" />;
            default: return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
        }
    };

    return (
        <div className="w-80 h-screen bg-gray-900 text-gray-100 flex flex-col border-r border-gray-800">
            <div className="p-4 border-b border-gray-800">
                <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
                    <History className="w-5 h-5 text-indigo-400" />
                    History
                </h2>
                <button
                    onClick={() => onSelectWorkflow('')}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg py-2 px-4 text-sm font-medium transition-colors flex items-center justify-center gap-2"
                >
                    <Activity className="w-4 h-4" />
                    New Workflow
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                {loading && workflows.length === 0 ? (
                    <div className="text-center py-10 text-gray-500">Loading...</div>
                ) : (
                    workflows.map((wf) => (
                        <button
                            key={wf.workflow_id}
                            onClick={() => onSelectWorkflow(wf.workflow_id)}
                            className={clsx(
                                "w-full text-left p-3 rounded-lg transition-all border border-transparent group relative pr-8",
                                currentWorkflowId === wf.workflow_id
                                    ? "bg-gray-800 border-gray-700 shadow-sm"
                                    : "hover:bg-gray-800/50"
                            )}
                        >
                            <div className="flex justify-between items-start mb-1">
                                {getStatusIcon(wf.status)}
                                <span className="text-xs text-gray-500">
                                    {formatDistanceToNow(new Date(wf.created_at), { addSuffix: true })}
                                </span>
                            </div>
                            <p className="text-sm text-gray-300 font-medium line-clamp-2 leading-snug group-hover:text-white">
                                {wf.state?.user_request || "Untitled Workflow"}
                            </p>

                            <div
                                onClick={(e) => deleteWorkflow(e, wf.workflow_id)}
                                className="absolute right-2 top-2 p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded-md transition-all cursor-pointer"
                                title="Delete Chat"
                            >
                                <Trash2 className="w-3.5 h-3.5 text-red-400" />
                            </div>
                        </button>
                    ))
                )}
            </div>

            <div className="p-4 border-t border-gray-800 text-xs text-center text-gray-500">
                v1.0.0
            </div>
        </div>
    );
};
