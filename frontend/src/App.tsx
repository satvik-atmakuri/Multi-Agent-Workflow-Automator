import { useState } from 'react';
import { CreateWorkflow } from './components/CreateWorkflow';
import { StatusDashboard } from './components/StatusDashboard';
import { Sidebar } from './components/Sidebar';
import { PreferencesModal } from './components/PreferencesModal';
import { Bot, RotateCcw, Settings } from 'lucide-react';

function App() {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isPrefsOpen, setIsPrefsOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        currentWorkflowId={workflowId}
        onSelectWorkflow={setWorkflowId}
      />

      {/* Main Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 shrink-0">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                Agentic Workflow Automator
              </h1>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsPrefsOpen(true)}
                className="flex items-center text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
                title="User Preferences"
              >
                <Settings className="w-5 h-5" />
              </button>

              {workflowId && (
                <button
                  onClick={() => setWorkflowId(null)}
                  className="flex items-center text-sm font-medium text-gray-500 hover:text-blue-600 transition-colors"
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  New Workflow
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-5xl mx-auto">
            {!workflowId ? (
              <div className="animate-in fade-in zoom-in duration-300">
                <div className="text-center mb-10">
                  <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl mb-4">
                    What can the agents do for you?
                  </h2>
                  <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                    Our multi-agent system plans, researches, and synthesizes complex tasks automatically.
                  </p>
                </div>
                <CreateWorkflow onWorkflowCreated={setWorkflowId} />
              </div>
            ) : (
              <div key={workflowId} className="animate-in slide-in-from-right duration-300">
                <StatusDashboard workflowId={workflowId} />
              </div>
            )}
          </div>
        </main>
      </div>

      <PreferencesModal isOpen={isPrefsOpen} onClose={() => setIsPrefsOpen(false)} />
    </div>
  );
}

export default App;
