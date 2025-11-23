import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Upload, FileText, AlertTriangle, CheckCircle, XCircle, Download, Plus, Trash2, Search, TrendingUp, History } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ContractAnalyzer = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchKeywords();
    fetchHistory();
  }, []);

  const fetchKeywords = async () => {
    try {
      const response = await axios.get(`${API}/keywords`);
      setKeywords(response.data);
    } catch (error) {
      console.error('Failed to fetch keywords:', error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/history`);
      setAnalysisHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const addKeyword = async () => {
    if (!newKeyword.trim()) {
      toast.error('Введите ключевое слово');
      return;
    }

    try {
      await axios.post(`${API}/keywords`, { keyword: newKeyword });
      toast.success('Ключевое слово добавлено');
      setNewKeyword('');
      fetchKeywords();
    } catch (error) {
      toast.error('Ошибка при добавлении ключевого слова');
    }
  };

  const deleteKeyword = async (keywordId) => {
    try {
      await axios.delete(`${API}/keywords/${keywordId}`);
      toast.success('Ключевое слово удалено');
      fetchKeywords();
    } catch (error) {
      toast.error('Ошибка при удалении');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    const allowedExtensions = ['.txt', '.docx', '.pdf'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowedExtensions.includes(fileExtension)) {
      toast.error(`Неподдерживаемый формат файла. Разрешены: ${allowedExtensions.join(', ')}`);
      return;
    }

    setSelectedFile(file);
    setAnalysisResult(null);
    toast.success(`Файл выбран: ${file.name}`);
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const analyzeContract = async () => {
    if (!selectedFile) {
      toast.error('Пожалуйста, выберите файл');
      return;
    }

    setAnalyzing(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API}/analyze`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysisResult(response.data);
      toast.success('Анализ завершен!');
      fetchHistory();
    } catch (error) {
      console.error('Analysis error:', error);
      toast.error(error.response?.data?.detail || 'Ошибка при анализе документа');
    } finally {
      setAnalyzing(false);
    }
  };

  const downloadReport = async (reportId, format) => {
    try {
      const response = await axios.get(`${API}/report/${reportId}/${format}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Отчет ${format.toUpperCase()} скачан`);
    } catch (error) {
      toast.error('Ошибка при скачивании отчета');
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      LOW: 'bg-green-500',
      MEDIUM: 'bg-amber-500',
      HIGH: 'bg-red-500',
    };
    return colors[level] || 'bg-gray-500';
  };

  const getRiskIcon = (level) => {
    if (level === 'LOW') return <CheckCircle className="w-5 h-5" />;
    if (level === 'MEDIUM') return <AlertTriangle className="w-5 h-5" />;
    return <XCircle className="w-5 h-5" />;
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-[#121212]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#00BFFF]/10 rounded-lg">
                <FileText className="w-8 h-8 text-[#00BFFF]" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-[#00BFFF]">LawAssistant</h1>
                <p className="text-sm text-gray-400">Анализ договоров с AI</p>
              </div>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" className="border-[#00BFFF] text-[#00BFFF] hover:bg-[#00BFFF]/10" data-testid="history-button">
                  <History className="w-4 h-4 mr-2" />
                  История
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-[#121212] border-gray-800 max-w-3xl">
                <DialogHeader>
                  <DialogTitle className="text-[#00BFFF]">История анализов</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    Последние проанализированные документы
                  </DialogDescription>
                </DialogHeader>
                <ScrollArea className="h-[400px] pr-4">
                  <div className="space-y-3">
                    {analysisHistory.map((item, index) => (
                      <Card key={index} className="bg-[#1a1a1a] border-gray-700" data-testid={`history-item-${index}`}>
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-semibold text-gray-100">{item.filename}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                {new Date(item.created_at).toLocaleString('ru-RU')}
                              </p>
                            </div>
                            <Badge className={`${getRiskColor(item.risk_level)} text-white`}>
                              {item.risk_level}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - File Upload & Keywords */}
          <div className="lg:col-span-1 space-y-6">
            {/* File Upload */}
            <Card className="bg-[#121212] border-gray-800" data-testid="upload-card">
              <CardHeader>
                <CardTitle className="text-[#00BFFF] flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  Загрузка файла
                </CardTitle>
                <CardDescription className="text-gray-400">
                  .txt, .docx, .pdf
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className={`file-upload-area ${
                    dragActive ? 'active border-[#00BFFF] bg-[#00BFFF]/5' : 'border-gray-700'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('file-input').click()}
                  data-testid="file-upload-area"
                >
                  <input
                    id="file-input"
                    type="file"
                    accept=".txt,.docx,.pdf"
                    onChange={handleFileInput}
                    className="hidden"
                    data-testid="file-input"
                  />
                  <Upload className="w-12 h-12 text-[#00BFFF] mx-auto mb-4" />
                  <p className="text-gray-300 font-medium mb-2">
                    {selectedFile ? selectedFile.name : 'Перетащите файл сюда'}
                  </p>
                  <p className="text-gray-500 text-sm">или нажмите для выбора</p>
                </div>

                <Button
                  onClick={analyzeContract}
                  disabled={!selectedFile || analyzing}
                  className="w-full mt-6 bg-[#00BFFF] hover:bg-[#00a8e6] text-black font-semibold"
                  data-testid="analyze-button"
                >
                  {analyzing ? (
                    <>
                      <div className="spinner mr-2" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></div>
                      Анализирую...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4 mr-2" />
                      Анализировать
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Custom Keywords */}
            <Card className="bg-[#121212] border-gray-800" data-testid="keywords-card">
              <CardHeader>
                <CardTitle className="text-[#00BFFF] flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  Свои ключевые слова
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Добавьте фразы для отслеживания
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2 mb-4">
                  <Input
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                    placeholder="Добавить ключевое слово"
                    className="input-field border-gray-700 focus:border-[#00BFFF]"
                    data-testid="keyword-input"
                  />
                  <Button
                    onClick={addKeyword}
                    size="icon"
                    className="bg-[#00BFFF] hover:bg-[#00a8e6] text-black"
                    data-testid="add-keyword-button"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>

                <ScrollArea className="h-[200px]">
                  <div className="space-y-2">
                    {keywords.map((kw) => (
                      <div
                        key={kw.id}
                        className="flex items-center justify-between bg-[#1a1a1a] p-3 rounded-lg border border-gray-700"
                        data-testid={`keyword-item-${kw.id}`}
                      >
                        <span className="text-sm text-gray-300">{kw.keyword}</span>
                        <Button
                          onClick={() => deleteKeyword(kw.id)}
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                          data-testid={`delete-keyword-${kw.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Analysis Results */}
          <div className="lg:col-span-2">
            {!analysisResult ? (
              <Card className="bg-[#121212] border-gray-800 border-dashed" data-testid="empty-state">
                <CardContent className="flex flex-col items-center justify-center py-24">
                  <FileText className="w-24 h-24 text-gray-600 mb-6" />
                  <h3 className="text-2xl font-semibold text-gray-400 mb-2">Результаты анализа</h3>
                  <p className="text-gray-500 text-center max-w-md">
                    Загрузите договор и нажмите "Анализировать" для получения подробного отчета о рисках
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6 fade-in" data-testid="analysis-results">
                {/* Risk Level Card */}
                <Card className="bg-[#121212] border-gray-800">
                  <CardContent className="pt-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400 mb-2">Уровень риска</p>
                        <div className={`risk-badge risk-${analysisResult.risk_level.toLowerCase()}`} data-testid="risk-badge">
                          {getRiskIcon(analysisResult.risk_level)}
                          {analysisResult.risk_level}
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <Button
                          onClick={() => downloadReport(analysisResult.id, 'json')}
                          variant="outline"
                          className="border-[#00BFFF] text-[#00BFFF] hover:bg-[#00BFFF]/10"
                          data-testid="download-json-button"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          JSON
                        </Button>
                        <Button
                          onClick={() => downloadReport(analysisResult.id, 'html')}
                          variant="outline"
                          className="border-[#00BFFF] text-[#00BFFF] hover:bg-[#00BFFF]/10"
                          data-testid="download-html-button"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          HTML
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Dangerous Phrases */}
                <Card className="bg-[#121212] border-gray-800" data-testid="dangerous-phrases-card">
                  <CardHeader>
                    <CardTitle className="text-[#00BFFF] flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5" />
                      Опасные фразы ({analysisResult.dangerous_phrases.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {analysisResult.dangerous_phrases.length === 0 ? (
                      <p className="text-gray-400 text-center py-8">Опасные фразы не обнаружены ✅</p>
                    ) : (
                      <ScrollArea className="h-[300px]">
                        <div className="space-y-3">
                          {analysisResult.dangerous_phrases.map((phrase, index) => (
                            <div
                              key={index}
                              className="bg-[#1a1a1a] p-4 rounded-lg border-l-4 border-[#00BFFF]"
                              data-testid={`danger-phrase-${index}`}
                            >
                              <p className="font-semibold text-[#00BFFF] mb-2">{phrase.phrase}</p>
                              <p className="text-sm text-gray-400">...{phrase.context}...</p>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    )}
                  </CardContent>
                </Card>

                {/* Missing Sections */}
                <Card className="bg-[#121212] border-gray-800" data-testid="missing-sections-card">
                  <CardHeader>
                    <CardTitle className="text-[#00BFFF] flex items-center gap-2">
                      <XCircle className="w-5 h-5" />
                      Отсутствующие разделы ({analysisResult.missing_sections.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {analysisResult.missing_sections.length === 0 ? (
                      <p className="text-gray-400 text-center py-8">Все обязательные разделы присутствуют ✅</p>
                    ) : (
                      <div className="space-y-2">
                        {analysisResult.missing_sections.map((section, index) => (
                          <div
                            key={index}
                            className="bg-red-500/10 border border-red-500/30 p-3 rounded-lg flex items-center gap-3"
                            data-testid={`missing-section-${index}`}
                          >
                            <XCircle className="w-5 h-5 text-red-400" />
                            <span className="text-gray-300">{section}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* AI Analysis */}
                {analysisResult.ai_analysis && (
                  <Card className="bg-gradient-to-br from-[#1a2a3a] to-[#2a1a3a] border-[#00BFFF]" data-testid="ai-analysis-card">
                    <CardHeader>
                      <CardTitle className="text-[#00BFFF] flex items-center gap-2">
                        <TrendingUp className="w-5 h-5" />
                        AI-анализ договора
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="prose prose-invert max-w-none">
                        <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">
                          {analysisResult.ai_analysis}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-20 py-8 bg-[#121212]/50">
        <div className="container mx-auto px-6">
          <div className="flex items-center justify-between">
            <p className="text-gray-500 text-sm">
              © 2025 LawAssistant. Все права защищены.
            </p>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#00BFFF] hover:text-[#00a8e6] text-sm flex items-center gap-2 transition-colors"
              data-testid="github-link"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" clipRule="evenodd" />
              </svg>
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default ContractAnalyzer;
