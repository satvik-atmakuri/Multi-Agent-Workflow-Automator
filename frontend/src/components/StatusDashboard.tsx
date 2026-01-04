import { useEffect, useState } from 'react';
import axios from 'axios';
import { CheckCircle2, PlayCircle, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

import { ChatInterface } from './ChatInterface';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

interface WorkflowState {
    workflow_id: string;
    status: 'planning' | 'awaiting_clarification' | 'researching' | 'synthesizing' | 'validating' | 'completed' | 'failed' | 'started';
    state: any;
    final_output?: any;
}

interface StatusDashboardProps {
    workflowId: string;
}

const STEPS = [
    { id: 'planning', label: 'Planning', icon: PlayCircle },
    { id: 'researching', label: 'Researching', icon: Loader2 },
    { id: 'synthesizing', label: 'Synthesizing', icon: Loader2 },
    { id: 'completed', label: 'Complete', icon: CheckCircle2 },
];

export function StatusDashboard({ workflowId }: StatusDashboardProps) {
    const [data, setData] = useState<WorkflowState | null>(null);
    const [error, setError] = useState<string | null>(null);

    const pollStatus = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/workflows/${workflowId}`);
            setData(response.data);
            setError(null);
        } catch (err) {
            console.error(err);
            setError('Failed to fetch status');
        }
    };

    useEffect(() => {
        pollStatus();
        const interval = setInterval(pollStatus, 2000);
        return () => clearInterval(interval);
    }, [workflowId]);

    if (error) return <div className="text-red-500">{error}</div>;
    if (!data) return <div className="flex items-center justify-center p-8"><Loader2 className="animate-spin text-blue-500" /></div>;

    const currentStepIndex = STEPS.findIndex(s => s.id === data.status) !== -1
        ? STEPS.findIndex(s => s.id === data.status)
        : (data.status === 'awaiting_clarification' ? 0 : -1);
    // clarification usually happens during/after planning but before researching

    return (
        <div className="w-full max-w-7xl mx-auto space-y-6">
            {/* Progress Steps */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex justify-between items-center overflow-x-auto">
                {STEPS.map((step, idx) => {
                    const Icon = step.icon;
                    const isActive = data.status === step.id;
                    const isCompleted = idx < currentStepIndex || data.status === 'completed';

                    return (
                        <div key={step.id} className="flex flex-col items-center min-w-[100px]">
                            <div
                                className={clsx(
                                    "w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-all",
                                    isActive ? "bg-blue-100 text-blue-600 ring-4 ring-blue-50" :
                                        isCompleted ? "bg-green-100 text-green-600" : "bg-gray-100 text-gray-400"
                                )}
                            >
                                <Icon className={clsx("w-5 h-5", isActive && step.id !== 'completed' && "animate-pulse")} />
                            </div>
                            <span className={clsx(
                                "text-sm font-medium",
                                isActive ? "text-blue-600" : isCompleted ? "text-green-600" : "text-gray-400"
                            )}>
                                {step.label}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Main Content Area - ChatGPT Style */}
            <div className="bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden flex flex-col min-h-[600px]">

                {/* Status Banner / Metadata Header */}
                <div className="bg-gray-50 border-b border-gray-200 p-4 flex justify-between items-center text-sm">
                    <div className="flex items-center gap-3">
                        <div className={clsx(
                            "px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wide",
                            data.status === 'failed' ? "bg-red-100 text-red-700" :
                                data.status === 'completed' ? "bg-green-100 text-green-700" :
                                    "bg-blue-100 text-blue-700"
                        )}>
                            {data.status.replace('_', ' ')}
                        </div>
                        <span className="text-gray-500">ID: {workflowId.slice(0, 8)}...</span>
                    </div>
                    <div className="text-gray-400">
                        {new Date(data.state.created_at).toLocaleString()}
                    </div>
                </div>

                {/* Chat / Results View - Always Visible */}
                <ChatInterface
                    workflowId={workflowId}
                    initialHistory={data.state.chat_history || []}
                    userRequest={data.state.user_request}
                    finalOutput={data.final_output}
                    status={data.status}
                    clarificationQuestions={data.state.clarification_questions}
                    onFeedbackSubmit={pollStatus}
                />
            </div>
        </div>
    );
}

