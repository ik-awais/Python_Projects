import React, { useState, useEffect } from 'react';

interface FileInfo {
  id: string;
  name: string;
  size: number;
  type: string;
  category: string;
  icon: string;
  upload_time: string;
  path: string;
  metadata?: any;
}

interface FileListProps {
  files: FileInfo[];
  onFilesChange?: (files: FileInfo[]) => void;
  selectedFiles?: string[];
  onSelectionChange?: (selectedFiles: string[]) => void;
  showActions?: boolean;
}

const FileList: React.FC<FileListProps> = ({ 
  files, 
  onFilesChange, 
  selectedFiles = [], 
  onSelectionChange,
  showActions = true 
}) => {
  const [deleting, setDeleting] = useState<string[]>([]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleDelete = async (fileId: string) => {
    setDeleting([...deleting, fileId]);
    
    try {
      const response = await fetch(`http://localhost:8000/api/files/${fileId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const updatedFiles = files.filter(f => f.id !== fileId);
        onFilesChange?.(updatedFiles);
      } else {
        console.error('Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
    } finally {
      setDeleting(deleting.filter(id => id !== fileId));
    }
  };

  const handleSelect = (fileId: string, checked: boolean) => {
    let newSelection: string[];
    if (checked) {
      newSelection = [...selectedFiles, fileId];
    } else {
      newSelection = selectedFiles.filter(id => id !== fileId);
    }
    onSelectionChange?.(newSelection);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange?.(files.map(f => f.id));
    } else {
      onSelectionChange?.([]);
    }
  };

  const getCategoryColor = (category: string): string => {
    const colors = {
      pdf: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      docx: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      xlsx: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      pptx: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      txt: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      csv: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      image: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
      video: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
      audio: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      html: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
    };
    return colors[category as keyof typeof colors] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 mx-auto bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <span className="text-2xl">📁</span>
        </div>
        <p className="text-gray-500 dark:text-gray-400">No files uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {onSelectionChange && (
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={selectedFiles.length === files.length && files.length > 0}
                onChange={(e) => handleSelectAll(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Select All ({selectedFiles.length}/{files.length})
              </span>
            </label>
          )}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {files.length} file{files.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* File List */}
      <div className="space-y-2">
        {files.map((file) => (
          <div
            key={file.id}
            className={`
              bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4
              hover:shadow-md transition-all duration-200
              ${selectedFiles.includes(file.id) ? 'ring-2 ring-blue-500' : ''}
            `}
          >
            <div className="flex items-center space-x-4">
              {/* Checkbox */}
              {onSelectionChange && (
                <input
                  type="checkbox"
                  checked={selectedFiles.includes(file.id)}
                  onChange={(e) => handleSelect(file.id, e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              )}

              {/* File Icon */}
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                  <span className="text-xl">{file.icon}</span>
                </div>
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {file.name}
                  </h3>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(file.category)}`}>
                    {file.category}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>{formatFileSize(file.size)}</span>
                  <span>•</span>
                  <span>{formatDate(file.upload_time)}</span>
                  {file.metadata?.pages && (
                    <>
                      <span>•</span>
                      <span>{file.metadata.pages} pages</span>
                    </>
                  )}
                </div>
              </div>

              {/* Actions */}
              {showActions && (
                <div className="flex items-center space-x-2">
                  <button
                    className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    title="Download"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(file.id)}
                    disabled={deleting.includes(file.id)}
                    className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors disabled:opacity-50"
                    title="Delete"
                  >
                    {deleting.includes(file.id) ? (
                      <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FileList;
