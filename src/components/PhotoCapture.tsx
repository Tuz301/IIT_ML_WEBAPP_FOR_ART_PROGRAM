import React, { useRef, useState } from 'react';
import Webcam from 'react-webcam';

const PhotoCapture: React.FC = () => {
  const webcamRef = useRef<Webcam>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [error, setError] = useState<string>('');

  const capture = () => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setCapturedImage(imageSrc);
        setError('');
      } else {
        setError('Failed to capture image');
      }
    }
  };

  const retake = () => {
    setCapturedImage(null);
    setError('');
  };

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="text-lg font-semibold mb-2">Photo/Document Capture</h3>
      {error && <p className="text-red-500 mb-2">{error}</p>}
      {!capturedImage ? (
        <div>
          <Webcam
            audio={false}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            videoConstraints={{
              width: 1280,
              height: 720,
              facingMode: 'environment' // Use back camera on mobile
            }}
            className="w-full max-w-md h-auto border rounded mb-2"
          />
          <button
            onClick={capture}
            className="px-4 py-2 bg-blue-500 text-white rounded"
          >
            Capture Photo
          </button>
        </div>
      ) : (
        <div>
          <img
            src={capturedImage}
            alt="Captured"
            className="w-full max-w-md h-auto border rounded mb-2"
          />
          <div className="flex gap-2">
            <button
              onClick={retake}
              className="px-4 py-2 bg-gray-500 text-white rounded"
            >
              Retake
            </button>
            <button
              onClick={() => {
                // In a real app, this would upload to server
                alert('Photo saved locally');
              }}
              className="px-4 py-2 bg-green-500 text-white rounded"
            >
              Save Photo
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotoCapture;
