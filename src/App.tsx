import React, { useState, useRef } from 'react';
import { Mic, Upload, MessageSquare, MapPin, AlertTriangle, Building2, FileAudio, Loader2, Play, Square as Stop, Database, TrendingUp, Clock, Users } from 'lucide-react';

// API Configuration - Update this URL after deploying to Render
const API_BASE_URL = 'http://localhost:8000'; // Change to your deployed backend URL

interface AnalysisResult {
  transcription: string;
  recognition_service: string;
  location: {
    latitude: string | null;
    longitude: string | null;
    address: string | null;
    confidence: string;
  };
  pollution_type: string;
  recommendation: string;
  responsible_agency: string;
  severity_level?: string;
  immediate_actions?: string;
  long_term_solution?: string;
  raw_cohere_response: any;
}

interface QueryResult {
  query: string;
  sql_query: string;
  result: any[];
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      setRecordingTime(0);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioFile = new File([audioBlob], `pollution-report-${Date.now()}.wav`, { type: 'audio/wav' });
        setAudioFile(audioFile);
        stream.getTracks().forEach(track => track.stop());
        
        if (recordingIntervalRef.current) {
          clearInterval(recordingIntervalRef.current);
        }
      };

      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setError(null);
      
      // Start recording timer
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      setError('Failed to access microphone. Please check permissions and try again.');
      console.error('Recording error:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type.includes('audio') || file.name.endsWith('.wav')) {
        setAudioFile(file);
        setError(null);
      } else {
        setError('Please select a valid audio file (.wav, .mp3, .m4a)');
      }
    }
  };

  const analyzeAudio = async () => {
    if (!audioFile) return;

    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      formData.append('file', audioFile);

      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const result = await response.json();
      setAnalysisResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      setError(`${errorMessage}. Please ensure the backend server is running.`);
      console.error('Analysis error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const askQuestion = async () => {
    if (!query.trim()) return;

    setIsQuerying(true);
    setError(null);
    setQueryResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/ask?q=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const result = await response.json();
      setQueryResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Query failed';
      setError(`${errorMessage}. Please ensure the backend server is running.`);
      console.error('Query error:', err);
    } finally {
      setIsQuerying(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'low': return 'text-green-700 bg-green-100 border-green-300';
      case 'medium': return 'text-yellow-700 bg-yellow-100 border-yellow-300';
      case 'high': return 'text-orange-700 bg-orange-100 border-orange-300';
      case 'critical': return 'text-red-700 bg-red-100 border-red-300';
      default: return 'text-gray-700 bg-gray-100 border-gray-300';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const clearResults = () => {
    setAnalysisResult(null);
    setQueryResult(null);
    setError(null);
    setAudioFile(null);
    setQuery('');
  };

  const quickQueries = [
    "Show me recent pollution reports",
    "What are the most common pollution types?",
    "List all water pollution incidents",
    "Show reports with location data"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-green-500 to-blue-500 rounded-xl">
                <AlertTriangle className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                  AI Pollution Analyzer
                </h1>
                <p className="text-gray-600">Environmental incident reporting with AI analysis</p>
              </div>
            </div>
            
            {(analysisResult || queryResult) && (
              <button
                onClick={clearResults}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Clear Results
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Audio Analysis Section */}
          <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center mb-6">
              <div className="p-2 bg-blue-100 rounded-lg mr-3">
                <FileAudio className="h-6 w-6 text-blue-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900">Audio Analysis</h2>
            </div>

            {/* Recording Controls */}
            <div className="space-y-4 mb-6">
              <div className="flex space-x-3">
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`flex-1 flex items-center justify-center px-6 py-4 rounded-xl font-semibold transition-all duration-200 transform hover:scale-105 ${
                    isRecording
                      ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg'
                      : 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg'
                  }`}
                >
                  {isRecording ? (
                    <>
                      <Stop className="h-5 w-5 mr-2" />
                      Stop Recording
                    </>
                  ) : (
                    <>
                      <Mic className="h-5 w-5 mr-2" />
                      Start Recording
                    </>
                  )}
                </button>

                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 flex items-center justify-center px-6 py-4 bg-gray-600 hover:bg-gray-700 text-white rounded-xl font-semibold transition-all duration-200 transform hover:scale-105 shadow-lg"
                >
                  <Upload className="h-5 w-5 mr-2" />
                  Upload Audio
                </button>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,.wav,.mp3,.m4a"
                onChange={handleFileUpload}
                className="hidden"
              />

              {isRecording && (
                <div className="p-4 bg-red-50 rounded-xl border border-red-200 animate-pulse">
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
                    <p className="text-red-800 font-semibold">
                      Recording: {formatTime(recordingTime)}
                    </p>
                  </div>
                </div>
              )}

              {audioFile && !isRecording && (
                <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-800 font-semibold">{audioFile.name}</p>
                      <p className="text-green-600 text-sm">
                        Size: {(audioFile.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                      <Play className="h-4 w-4 text-white" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Analyze Button */}
            <button
              onClick={analyzeAudio}
              disabled={!audioFile || isAnalyzing}
              className="w-full flex items-center justify-center px-6 py-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-xl font-bold text-lg transition-all duration-200 disabled:cursor-not-allowed transform hover:scale-105 shadow-lg"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Analyzing Audio...
                </>
              ) : (
                <>
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Analyze Pollution Report
                </>
              )}
            </button>
          </div>

          {/* Database Query Section */}
          <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center mb-6">
              <div className="p-2 bg-purple-100 rounded-lg mr-3">
                <Database className="h-6 w-6 text-purple-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900">Data Insights</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Ask a Question
                </label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., 'Show me all water pollution incidents from last week'"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none transition-all"
                  rows={3}
                />
              </div>

              {/* Quick Query Buttons */}
              <div className="grid grid-cols-1 gap-2">
                <p className="text-sm font-medium text-gray-600 mb-2">Quick queries:</p>
                {quickQueries.map((quickQuery, index) => (
                  <button
                    key={index}
                    onClick={() => setQuery(quickQuery)}
                    className="text-left px-3 py-2 text-sm text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded-lg transition-colors"
                  >
                    {quickQuery}
                  </button>
                ))}
              </div>

              <button
                onClick={askQuestion}
                disabled={!query.trim() || isQuerying}
                className="w-full flex items-center justify-center px-6 py-3 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-xl font-semibold transition-all duration-200 disabled:cursor-not-allowed transform hover:scale-105 shadow-lg"
              >
                {isQuerying ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Processing Query...
                  </>
                ) : (
                  <>
                    <MessageSquare className="h-5 w-5 mr-2" />
                    Ask Question
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-8 p-4 bg-red-50 border border-red-200 rounded-xl">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0" />
              <div>
                <p className="text-red-800 font-semibold">Error</p>
                <p className="text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Analysis Results */}
        {analysisResult && (
          <div className="mt-8 bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center mb-6">
              <TrendingUp className="h-6 w-6 text-green-600 mr-2" />
              <h3 className="text-2xl font-bold text-gray-900">Analysis Results</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Transcription */}
              <div className="col-span-full">
                <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                  <MessageSquare className="h-5 w-5 mr-2 text-blue-600" />
                  Transcription
                </h4>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <p className="text-gray-800 leading-relaxed">{analysisResult.transcription}</p>
                  <div className="flex items-center mt-3 pt-3 border-t border-gray-300">
                    <Users className="h-4 w-4 text-gray-500 mr-1" />
                    <p className="text-sm text-gray-600">
                      Service: {analysisResult.recognition_service}
                    </p>
                  </div>
                </div>
              </div>

              {/* Pollution Type & Severity */}
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">Pollution Classification</h4>
                <div className="space-y-3">
                  <div className="p-4 bg-red-50 rounded-xl border border-red-200">
                    <p className="text-sm text-red-600 font-medium mb-1">Type</p>
                    <p className="text-red-800 font-bold capitalize text-lg">
                      {analysisResult.pollution_type}
                    </p>
                  </div>
                  
                  {analysisResult.severity_level && (
                    <div className={`p-3 rounded-xl border ${getSeverityColor(analysisResult.severity_level)}`}>
                      <p className="text-sm font-medium mb-1">Severity Level</p>
                      <p className="font-bold capitalize">
                        {analysisResult.severity_level}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Responsible Agency */}
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                  <Building2 className="h-5 w-5 mr-2" />
                  Responsible Agency
                </h4>
                <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                  <p className="text-blue-800 font-semibold">
                    {analysisResult.responsible_agency}
                  </p>
                </div>
              </div>

              {/* Location */}
              {analysisResult.location.address && (
                <div className="col-span-full">
                  <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                    <MapPin className="h-5 w-5 mr-2" />
                    Location Information
                  </h4>
                  <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                    <p className="text-green-800 font-medium">{analysisResult.location.address}</p>
                    {analysisResult.location.latitude && analysisResult.location.longitude && (
                      <p className="text-sm text-green-600 mt-2">
                        📍 {analysisResult.location.latitude}, {analysisResult.location.longitude}
                      </p>
                    )}
                    <div className="flex items-center mt-2">
                      <div className={`w-2 h-2 rounded-full mr-2 ${
                        analysisResult.location.confidence === 'high' ? 'bg-green-500' :
                        analysisResult.location.confidence === 'medium' ? 'bg-yellow-500' : 'bg-red-500'
                      }`}></div>
                      <p className="text-sm text-green-600 capitalize">
                        Confidence: {analysisResult.location.confidence}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div className="col-span-full space-y-4">
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">Cleanup Recommendation</h4>
                  <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-200">
                    <p className="text-yellow-800 leading-relaxed">{analysisResult.recommendation}</p>
                  </div>
                </div>

                {analysisResult.immediate_actions && (
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                      <Clock className="h-5 w-5 mr-2 text-orange-600" />
                      Immediate Actions
                    </h4>
                    <div className="p-4 bg-orange-50 rounded-xl border border-orange-200">
                      <p className="text-orange-800 leading-relaxed">{analysisResult.immediate_actions}</p>
                    </div>
                  </div>
                )}

                {analysisResult.long_term_solution && (
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 mb-3">Long-term Solution</h4>
                    <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-200">
                      <p className="text-indigo-800 leading-relaxed">{analysisResult.long_term_solution}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Query Results */}
        {queryResult && (
          <div className="mt-8 bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center mb-6">
              <Database className="h-6 w-6 text-purple-600 mr-2" />
              <h3 className="text-2xl font-bold text-gray-900">Query Results</h3>
            </div>
            
            <div className="space-y-6">
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">Your Question</h4>
                <div className="p-4 bg-purple-50 rounded-xl border border-purple-200">
                  <p className="text-purple-800 font-medium">{queryResult.query}</p>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">Generated SQL</h4>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 font-mono text-sm overflow-x-auto">
                  <code className="text-gray-800">{queryResult.sql_query}</code>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">
                  Results ({queryResult.result.length} records)
                </h4>
                <div className="overflow-x-auto">
                  {queryResult.result.length > 0 ? (
                    <div className="border border-gray-200 rounded-xl overflow-hidden">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            {Object.keys(queryResult.result[0]).map((key) => (
                              <th key={key} className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                {key.replace(/_/g, ' ')}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {queryResult.result.slice(0, 10).map((row, index) => (
                            <tr key={index} className="hover:bg-gray-50 transition-colors">
                              {Object.values(row).map((value, cellIndex) => (
                                <td key={cellIndex} className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                                  {value !== null ? String(value) : '-'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {queryResult.result.length > 10 && (
                        <div className="bg-gray-50 px-6 py-3 text-sm text-gray-600 text-center">
                          Showing first 10 of {queryResult.result.length} results
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 bg-gray-50 rounded-xl border border-gray-200 text-center">
                      <Database className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-600 font-medium">No results found</p>
                      <p className="text-gray-500 text-sm">Try a different query or check if data exists</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <p className="text-gray-600 mb-2">
              AI Pollution Analyzer - Powered by Cohere AI & OpenAI Whisper
            </p>
            <p className="text-sm text-gray-500">
              Environmental incident reporting with intelligent analysis
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;