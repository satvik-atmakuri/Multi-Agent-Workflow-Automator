import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { X, Plus, Trash2, Settings } from 'lucide-react';
import clsx from 'clsx';

interface Preference {
    key: string;
    value: string;
}

interface Props {
    isOpen: boolean;
    onClose: () => void;
}

export const PreferencesModal: React.FC<Props> = ({ isOpen, onClose }) => {
    const [preferences, setPreferences] = useState<Preference[]>([]);
    const [newKey, setNewKey] = useState('');
    const [newValue, setNewValue] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchPreferences();
        }
    }, [isOpen]);

    const fetchPreferences = async () => {
        try {
            const res = await axios.get('http://localhost:8000/api/preferences/');
            const prefsArray = Object.entries(res.data.preferences).map(([key, value]) => ({
                key,
                value: value as string
            }));
            setPreferences(prefsArray);
        } catch (error) {
            console.error("Failed to fetch preferences", error);
        }
    };

    const handleSave = async () => {
        if (!newKey || !newValue) return;
        setLoading(true);
        try {
            await axios.post('http://localhost:8000/api/preferences/', {
                key: newKey,
                value: newValue
            });
            await fetchPreferences();
            setNewKey('');
            setNewValue('');
        } catch (error) {
            console.error("Failed to save preference", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (key: string) => {
        try {
            await axios.delete(`http://localhost:8000/api/preferences/${key}`);
            await fetchPreferences();
        } catch (error) {
            console.error("Failed to delete preference", error);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6 animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                        <Settings className="w-5 h-5 text-indigo-600" />
                        User Preferences
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="space-y-4 mb-6 max-h-[60vh] overflow-y-auto">
                    {preferences.length === 0 ? (
                        <p className="text-gray-500 italic text-center py-4">No specific preferences set.</p>
                    ) : (
                        preferences.map((pref) => (
                            <div key={pref.key} className="flex items-center gap-3 bg-gray-50 p-3 rounded-lg border border-gray-100 group">
                                <div className="flex-1">
                                    <span className="font-semibold text-gray-700">{pref.key}:</span>
                                    <span className="ml-2 text-gray-600">{pref.value}</span>
                                </div>
                                <button
                                    onClick={() => handleDelete(pref.key)}
                                    className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))
                    )}
                </div>

                <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-100">
                    <h3 className="text-sm font-semibold text-indigo-900 mb-3">Add New Preference</h3>
                    <div className="flex gap-2 mb-2">
                        <input
                            type="text"
                            placeholder="Key (e.g. Conciseness)"
                            value={newKey}
                            onChange={(e) => setNewKey(e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <input
                            type="text"
                            placeholder="Value (e.g. High)"
                            value={newValue}
                            onChange={(e) => setNewValue(e.target.value)}
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={!newKey || !newValue || loading}
                        className={clsx(
                            "w-full flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium transition-colors",
                            !newKey || !newValue || loading
                                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                                : "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm"
                        )}
                    >
                        <Plus className="w-4 h-4" />
                        {loading ? 'Saving...' : 'Add Preference'}
                    </button>
                    <p className="text-xs text-indigo-600 mt-2">
                        These instructions will be injected into every agent planner prompt.
                    </p>
                </div>
            </div>
        </div>
    );
};
