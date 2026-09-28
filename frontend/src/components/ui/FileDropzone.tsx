import React, { useRef, useState } from 'react';
import { UploadCloud, X, FileText, CheckCircle2 } from 'lucide-react';
import { cn } from '../../utils/utils';

interface FileDropzoneProps {
  onFileSelect: (file: File | null) => void;
  accept?: string;
  maxSizeMB?: number;
  className?: string;
}

export function FileDropzone({ onFileSelect, accept = '.pdf', maxSizeMB = 50, className }: FileDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    if (accept === '.pdf' && file.type !== 'application/pdf') {
      setError('Only PDF files are allowed');
      return;
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size must be less than ${maxSizeMB}MB`);
      return;
    }
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const removeFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setError(null);
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-150',
          isDragActive ? 'border-[#1769D2] bg-[#EAF3FF]/40 ring-4 ring-[#1769D2]/10' : 'border-[#D9E2EC] hover:border-[#1769D2]/70 bg-[#F7F9FC] hover:bg-[#F0F4F8]',
          selectedFile ? 'border-[#16845B] bg-[#EAF7EE]/30 hover:border-[#16845B]' : '',
          error ? 'border-[#C53030] bg-[#FDF2F2]/30' : ''
        )}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !selectedFile && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={handleChange}
        />
        
        {selectedFile ? (
          <div className="flex items-center w-full max-w-md bg-white p-3.5 rounded-lg shadow-subtle border border-[#D9E2EC]">
            <div className="w-10 h-10 rounded-lg bg-[#EAF7EE] border border-[#B7E4C7] flex items-center justify-center text-[#16845B] mr-3 flex-shrink-0">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0 mr-2">
              <p className="text-xs font-semibold text-[#172B4D] truncate">
                {selectedFile.name}
              </p>
              <p className="text-[11px] text-[#5B6B7F] mt-0.5">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for ingestion
              </p>
            </div>
            <button
              onClick={removeFile}
              className="p-1 rounded-md text-[#5B6B7F] hover:text-[#C53030] hover:bg-[#FDF2F2] transition-colors"
              title="Remove file"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-xl bg-[#EAF3FF] border border-[#ADCFFF] flex items-center justify-center text-[#123B66] mb-3 transition-transform group-hover:scale-105">
              <UploadCloud className={cn('h-6 w-6 text-[#1769D2]', isDragActive && 'text-[#0B2545]')} />
            </div>
            <p className="text-xs font-semibold text-[#172B4D] tracking-tight">
              Click to select or drag and drop official cutoff PDF document
            </p>
            <p className="text-[11px] text-[#5B6B7F] mt-1">
              Supports State & All-India CAP cutoff allotment PDFs up to {maxSizeMB}MB
            </p>
          </div>
        )}
      </div>
      {error && <p className="mt-1.5 text-xs text-[#C53030] font-medium">{error}</p>}
    </div>
  );
}

export default FileDropzone;
