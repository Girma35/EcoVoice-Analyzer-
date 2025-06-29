import React, { useState, useRef } from 'react';
import { Mic, Upload, MessageSquare, MapPin, AlertTriangle, Building2, FileAudio, Loader2, Play, Stop } from 'lucide-react';

// API Configuration - Update this URL after deploying to Render
const API_BASE_URL = 'https://pollution-analyzer-api.onrender.com';

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
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
        setAudioFile(audioFile);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError('Failed to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'audio/wav') {
      setAudioFile(file);
      setError(null);
    } else {
      setError('Please select a valid .wav audio file');
    }
  };

  const analyzeAudio = async () => {
    if (!audioFile) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', audioFile);

      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      setAnalysisResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed. Please check if the backend is running.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const askQuestion = async () => {
    if (!query.trim()) return;

    setIsQuerying(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/ask?q=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Query failed: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      setQueryResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed. Please check if the backend is running.');
    } finally {
      setIsQuerying(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'low': return 'text-green-700 bg-green-100 border-green-200';
      case 'medium': return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'high': return 'text-orange-700 bg-orange-100 border-orange-200';
      case 'critical': return 'text-red-700 bg-red-100 border-red-200';
      default: return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      {/* Header */}
      <header className="bg-white shadow-lg border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <AlertTriangle className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">AI Pollution Analyzer</h1>
              <p className="text-gray-600">Report environmental incidents with voice analysis</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Audio Recording/Upload Section */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center">
              <FileAudio className="h-6 w-6 mr-2 text-blue-600" />
              Audio Analysis
            </h2>

            {/* Recording Controls */}
            <div className="space-y-4 mb-6">
              <div className="flex space-x-4">
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`flex-1 flex items-center justify-center px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                    isRecording
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
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
                  className="flex-1 flex items-center justify-center px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-all duration-200"
                >
                  <Upload className="h-5 w-5 mr-2" />
                  Upload WAV
                </button>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".wav"
                onChange={handleFileUpload}
                className="hidden"
              />

              {audioFile && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-blue-800 font-medium">
                    Audio file ready: {audioFile.name}
                  </p>
                  <p className="text-blue-600 text-sm">
                    Size: {(audioFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              )}
            </div>

            {/* Analyze Button */}
            <button
              onClick={analyzeAudio}
              disabled={!audioFile || isAnalyzing}
              className="w-full flex items-center justify-center px-6 py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-semibold text-lg transition-all duration-200 disabled:cursor-not-allowed"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Analyzing Audio...
                </>
              ) : (
                <>
                  <Play className="h-5 w-5 mr-2" />
                  Analyze Pollution Report
                </>
              )}
            </button>
          </div>

          {/* Database Query Section */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center">
              <MessageSquare className="h-6 w-6 mr-2 text-purple-600" />
              Ask Questions
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Natural Language Query
                </label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., 'Show me all water pollution incidents from last week' or 'What are the most common pollution types?'"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                  rows={3}
                />
              </div>

              <button
                onClick={askQuestion}
                disabled={!query.trim() || isQuerying}
                className="w-full flex items-center justify-center px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-all duration-200 disabled:cursor-not-allowed"
              >
                {isQuerying ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Processing Query...
                  </>
                ) : (
                  'Ask Question'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-8 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
              <p className="text-red-800 font-medium">Error</p>
            </div>
            <p className="text-red-700 mt-1">{error}</p>
          </div>
        )}

        {/* Analysis Results */}
        {analysisResult && (
          <div className="mt-8 bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Analysis Results</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Transcription */}
              <div className="col-span-full">
                <h4 className="text-lg font-medium text-gray-900 mb-2">Transcription</h4>
                <div className="p-4 bg-gray-50 rounded-lg border">
                  <p className="text-gray-800">{analysisResult.transcription}</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Service: {analysisResult.recognition_service}
                  </p>
                </div>
              </div>

              {/* Pollution Type */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-2">Pollution Type</h4>
                <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                  <p className="text-red-800 font-semibold capitalize">
                    {analysisResult.pollution_type}
                  </p>
                </div>
              </div>

              {/* Responsible Agency */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-2 flex items-center">
                  <Building2 className="h-5 w-5 mr-1" />
                  Responsible Agency
                </h4>
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-blue-800 font-medium">
                    {analysisResult.responsible_agency}
                  </p>
                </div>
              </div>

              {/* Location */}
              {analysisResult.location.address && (
                <div className="col-span-full">
                  <h4 className="text-lg font-medium text-gray-900 mb-2 flex items-center">
                    <MapPin className="h-5 w-5 mr-1" />
                    Location
                  </h4>
                  <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                    <p className="text-green-800">{analysisResult.location.address}</p>
                    {analysisResult.location.latitude && analysisResult.location.longitude && (
                      <p className="text-sm text-green-600 mt-1">
                        Coordinates: {analysisResult.location.latitude}, {analysisResult.location.longitude}
                      </p>
                    )}
                    <p className="text-sm text-green-600">
                      Confidence: {analysisResult.location.confidence}
                    </p>
                  </div>
                </div>
              )}

              {/* Recommendation */}
              <div className="col-span-full">
                <h4 className="text-lg font-medium text-gray-900 mb-2">Cleanup Recommendation</h4>
                <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-yellow-800">{analysisResult.recommendation}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Query Results */}
        {queryResult && (
          <div className="mt-8 bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Query Results</h3>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-2">Your Question</h4>
                <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                  <p className="text-purple-800">{queryResult.query}</p>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-2">Generated SQL</h4>
                <div className="p-3 bg-gray-50 rounded-lg border font-mono text-sm">
                  <p className="text-gray-800">{queryResult.sql_query}</p>
                </div>
              </div>

              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-2">Results</h4>
                <div className="overflow-x-auto">
                  {queryResult.result.length > 0 ? (
                    <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                      <thead className="bg-gray-50">
                        <tr>
                          {Object.keys(queryResult.result[0]).map((key) => (
                            <th key={key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {queryResult.result.map((row, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            {Object.values(row).map((value, cellIndex) => (
                              <td key={cellIndex} className="px-4 py-3 text-sm text-gray-900">
                                {String(value)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="p-4 bg-gray-50 rounded-lg border text-center">
                      <p className="text-gray-600">No results found</p>
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-600">
            AI Pollution Analyzer - Powered by Cohere AI & OpenAI Whisper
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;