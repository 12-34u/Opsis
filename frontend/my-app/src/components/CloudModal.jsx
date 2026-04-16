import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { collection, getDocs, doc, setDoc, deleteDoc } from 'firebase/firestore';
import './CloudModal.css';

const CloudModal = ({ isOpen, mode, userEmail, currentContent = '', currentFileName = '', onClose, onLoadComplete, onSaveComplete }) => {
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && mode === 'load') {
      fetchFiles();
    }
    if (isOpen && mode === 'save') {
      setSaveName(currentFileName && !currentFileName.startsWith('untitled_') ? currentFileName : '');
      setError(null);
    }
  }, [isOpen, mode]);

  const fetchFiles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const filesRef = collection(db, 'Users', userEmail, 'files');
      const snapshot = await getDocs(filesRef);
      const fetchedFiles = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setFiles(fetchedFiles);
    } catch (err) {
      setError("Failed to fetch cloud files. Check connection.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e, fileName) => {
    e.stopPropagation();
    if (!confirm(`Delete "${fileName}" from cloud?`)) return;
    try {
      await deleteDoc(doc(db, 'Users', userEmail, 'files', fileName));
      setFiles(prev => prev.filter(f => f.id !== fileName));
    } catch (err) {
      setError('Failed to delete file.');
      console.error(err);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!saveName.trim()) {
      setError("File name cannot be empty.");
      return;
    }
    
    // Validate filename formatting safely
    let finalName = saveName.trim().replace(/[^a-zA-Z0-9_\-.]/g, '');
    if (!finalName.includes('.')) {
      finalName += '.asm'; // Default extension
    }

    setIsLoading(true);
    setError(null);
    try {
      const fileDoc = doc(db, 'Users', userEmail, 'files', finalName);
      await setDoc(fileDoc, {
        name: finalName,
        content: currentContent,
        language: 'assembly',
        updatedAt: new Date().toISOString()
      });
      setIsLoading(false);
      onSaveComplete(finalName);
    } catch (err) {
      setIsLoading(false);
      setError("Failed to save to cloud. Check permissions.");
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="cloud-modal-overlay">
      <div className="cloud-modal">
        <div className="cloud-modal-header">
          <h3>{mode === 'save' ? 'Save to Cloud' : 'Load from Cloud'}</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        
        <div className="cloud-modal-body">
          {error && <div className="cloud-error">{error}</div>}

          {mode === 'save' ? (
            <form onSubmit={handleSave} className="cloud-save-form">
              <label>File Name</label>
              <div className="input-row">
                <input 
                  type="text" 
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="e.g. my_program.asm"
                  autoFocus
                />
                <button type="submit" disabled={isLoading || !saveName.trim()} className="cloud-submit-btn">
                  {isLoading ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          ) : (
            <div className="cloud-load-list">
              {isLoading ? (
                <div className="cloud-loading">Fetching your files...</div>
              ) : files.length === 0 ? (
                <div className="cloud-empty">No files found in your cloud storage.</div>
              ) : (
                <ul className="file-list">
                  {files.map(file => (
                    <li key={file.id} onClick={() => onLoadComplete(file)}>
                      <div className="file-info">
                        <span className="file-name">{file.name}</span>
                        <span className="file-date">
                          {new Date(file.updatedAt).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="file-actions">
                        <button className="load-inline-btn">Load</button>
                        <button className="delete-inline-btn" onClick={(e) => handleDelete(e, file.id)}>✕</button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CloudModal;
