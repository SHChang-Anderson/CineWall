import React, { useState } from 'react';

function ScannerControls({ onScanLocal, onScanGoogleDrive, loading }) {
  const [folderPath, setFolderPath] = useState('');

  const handleScanLocal = () => {
    if (folderPath) {
      onScanLocal(folderPath);
    } else {
      alert('Please enter a local folder path.');
    }
  };

  return (
    <div className="scanner-controls">
      <input
        type="text"
        value={folderPath}
        onChange={(e) => setFolderPath(e.target.value)}
        placeholder="Enter local movie folder path (e.g., /Volumes/Movies)"
        disabled={loading}
      />
      <button onClick={handleScanLocal} disabled={loading}>
        Scan Local Folder
      </button>
      <button onClick={onScanGoogleDrive} disabled={loading}>
        Scan Google Drive
      </button>
    </div>
  );
}

export default ScannerControls;
