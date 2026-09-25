import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { FileDropzone } from '../components/ui/FileDropzone';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { uploadPdf, processBatch } from '../api/imports';

export function ImportNewPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [round, setRound] = useState<number>(1);
  const [batchId, setBatchId] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return uploadPdf(file, year, round);
    },
    onSuccess: (data) => {
      toast.success('File uploaded successfully');
      setBatchId(data.import_batch_id);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Upload failed');
    }
  });

  const processMutation = useMutation({
    mutationFn: () => {
      if (!batchId) throw new Error('No batch selected');
      return processBatch(batchId);
    },
    onMutate: () => {
      setIsProcessing(true);
    },
    onSuccess: () => {
      toast.success('Processing completed');
      setIsProcessing(false);
      if (batchId) navigate(`/imports/${batchId}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Processing failed');
      setIsProcessing(false);
    }
  });

  const years = Array.from({ length: 10 }, (_, i) => {
    const y = new Date().getFullYear() - 2 + i;
    return { value: y, label: String(y) };
  });

  const rounds = [
    { value: 1, label: 'CAP Round I' },
    { value: 2, label: 'CAP Round II' },
    { value: 3, label: 'CAP Round III' },
    { value: 4, label: 'CAP Round IV' },
  ];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Import New CAP Cutoffs</h1>
      
      {!batchId ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Admission Year"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              options={years}
            />
            <Select
              label="CAP Round"
              value={round}
              onChange={(e) => setRound(Number(e.target.value))}
              options={rounds}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload PDF File
            </label>
            <FileDropzone onFileSelect={setFile} />
          </div>

          <div className="flex justify-end">
            <Button
              onClick={() => uploadMutation.mutate()}
              isLoading={uploadMutation.isPending}
              disabled={!file}
            >
              Upload PDF
            </Button>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6 text-center">
          <h3 className="text-lg font-medium text-gray-900">Upload Successful</h3>
          <p className="text-gray-500">
            The file has been saved. Click the button below to start extracting cutoff records.
            This may take a few minutes depending on the file size.
          </p>
          
          <Button
            onClick={() => processMutation.mutate()}
            isLoading={isProcessing}
            size="lg"
            className="w-full sm:w-auto"
          >
            {isProcessing ? 'Processing PDF...' : 'Start Processing'}
          </Button>
        </div>
      )}
    </div>
  );
}
