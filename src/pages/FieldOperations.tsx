 import React from 'react';
import LocationTracker from '../components/LocationTracker';
import VoiceNote from '../components/VoiceNote';
import BarcodeScanner from '../components/BarcodeScanner';
import PhotoCapture from '../components/PhotoCapture';
import EmergencyContact from '../components/EmergencyContact';

const FieldOperations: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Field Operations</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Location Tracking */}
          <div className="bg-white rounded-lg shadow">
            <LocationTracker />
          </div>

          {/* Voice Notes */}
          <div className="bg-white rounded-lg shadow">
            <VoiceNote />
          </div>

          {/* Barcode Scanner */}
          <div className="bg-white rounded-lg shadow">
            <BarcodeScanner />
          </div>

          {/* Photo Capture */}
          <div className="bg-white rounded-lg shadow">
            <PhotoCapture />
          </div>
        </div>

        {/* Emergency Contact - Full Width */}
        <div className="mt-6 bg-white rounded-lg shadow">
          <EmergencyContact />
        </div>

        {/* Field Data Sync Status */}
        <div className="mt-6 bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-2">Data Synchronization</h3>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">Online - Data synced</span>
          </div>
          <button className="mt-2 px-4 py-2 bg-blue-500 text-white rounded">
            Sync Now
          </button>
        </div>
      </div>
    </div>
  );
};

export default FieldOperations;
