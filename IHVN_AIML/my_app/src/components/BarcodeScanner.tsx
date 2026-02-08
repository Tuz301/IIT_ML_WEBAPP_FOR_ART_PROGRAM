import React, { useRef, useEffect, useState } from 'react';
import { BrowserMultiFormatReader } from '@zxing/library';

const BarcodeScanner: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isScanning, setIsScanning] = useState(false);
  const codeReaderRef = useRef<BrowserMultiFormatReader | null>(null);

  useEffect(() => {
    codeReaderRef.current = new BrowserMultiFormatReader();

    return () => {
      if (codeReaderRef.current) {
        codeReaderRef.current.reset();
      }
    };
  }, []);

  const startScanning = async () => {
    if (!videoRef.current || !codeReaderRef.current) return;

    try {
      setError('');
      setIsScanning(true);
      const result = await codeReaderRef.current.decodeOnceFromVideoDevice(undefined, videoRef.current);
      setResult(result.getText());
      setIsScanning(false);
    } catch (err) {
      setError('Failed to scan barcode. Please try again.');
      setIsScanning(false);
    }
  };

  const stopScanning = () => {
    if (codeReaderRef.current) {
      codeReaderRef.current.reset();
    }
    setIsScanning(false);
  };

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="text-lg font-semibold mb-2">Barcode/QR Code Scanner</h3>
      {error && <p className="text-red-500 mb-2">{error}</p>}
      <div className="flex gap-2 mb-2">
        <button
          onClick={isScanning ? stopScanning : startScanning}
          className={`px-4 py-2 rounded ${isScanning ? 'bg-red-500 text-white' : 'bg-green-500 text-white'}`}
        >
          {isScanning ? 'Stop Scanning' : 'Start Scanning'}
        </button>
      </div>
      <video
        ref={videoRef}
        style={{ width: '100%', maxWidth: '400px', height: '300px' }}
        className="border rounded mb-2"
      />
      {result && (
        <div className="p-2 bg-gray-100 rounded">
          <strong>Scanned Result:</strong> {result}
        </div>
      )}
    </div>
  );
};

export default BarcodeScanner;
