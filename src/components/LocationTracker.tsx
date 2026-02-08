import React, { useState, useEffect } from 'react';
import { MapPin, Navigation, Clock, RefreshCw } from 'lucide-react';

interface LocationData {
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  timestamp: string | null;
  error: string | null;
}

const LocationTracker: React.FC = () => {
  const [location, setLocation] = useState<LocationData>({
    latitude: null,
    longitude: null,
    accuracy: null,
    timestamp: null,
    error: null
  });
  const [isTracking, setIsTracking] = useState(false);
  const [watchId, setWatchId] = useState<number | null>(null);

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      setLocation(prev => ({ ...prev, error: 'Geolocation is not supported by your browser' }));
      return;
    }

    setIsTracking(true);
    setLocation(prev => ({ ...prev, error: null }));

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: new Date().toLocaleString(),
          error: null
        });
        setIsTracking(false);
      },
      (error) => {
        setLocation(prev => ({
          ...prev,
          error: getErrorMessage(error.code)
        }));
        setIsTracking(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  };

  const startTracking = () => {
    if (!navigator.geolocation) {
      setLocation(prev => ({ ...prev, error: 'Geolocation is not supported by your browser' }));
      return;
    }

    setIsTracking(true);
    setLocation(prev => ({ ...prev, error: null }));

    const id = navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: new Date().toLocaleString(),
          error: null
        });
      },
      (error) => {
        setLocation(prev => ({
          ...prev,
          error: getErrorMessage(error.code)
        }));
        stopTracking();
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );

    setWatchId(id);
  };

  const stopTracking = () => {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
      setIsTracking(false);
    }
  };

  const getErrorMessage = (code: number): string => {
    switch (code) {
      case 1:
        return 'Location permission denied. Please enable location access.';
      case 2:
        return 'Unable to determine location. Position unavailable.';
      case 3:
        return 'Location request timed out. Please try again.';
      default:
        return 'An unknown error occurred while getting location.';
    }
  };

  const openInMaps = () => {
    if (location.latitude && location.longitude) {
      const url = `https://www.google.com/maps?q=${location.latitude},${location.longitude}`;
      window.open(url, '_blank');
    }
  };

  useEffect(() => {
    return () => {
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [watchId]);

  return (
    <div className="p-4 border rounded-lg">
      <h3 className="text-lg font-semibold mb-2">GPS Location Tracker</h3>

      {location.error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {location.error}
        </div>
      )}

      <div className="space-y-3 mb-4">
        <div className="flex items-center space-x-2">
          <MapPin className="w-5 h-5 text-blue-500" />
          <div className="flex-1">
            <div className="text-xs text-gray-500">Latitude</div>
            <div className="font-mono font-semibold">
              {location.latitude !== null ? location.latitude.toFixed(6) : '---'}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <MapPin className="w-5 h-5 text-green-500" />
          <div className="flex-1">
            <div className="text-xs text-gray-500">Longitude</div>
            <div className="font-mono font-semibold">
              {location.longitude !== null ? location.longitude.toFixed(6) : '---'}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Navigation className="w-5 h-5 text-purple-500" />
          <div className="flex-1">
            <div className="text-xs text-gray-500">Accuracy</div>
            <div className="font-mono font-semibold">
              {location.accuracy !== null ? `±${location.accuracy.toFixed(0)}m` : '---'}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Clock className="w-5 h-5 text-orange-500" />
          <div className="flex-1">
            <div className="text-xs text-gray-500">Last Updated</div>
            <div className="font-mono font-semibold text-sm">
              {location.timestamp || '---'}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={getCurrentLocation}
          disabled={isTracking}
          className="flex-1 min-w-[120px] px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${isTracking ? 'animate-spin' : ''}`} />
          <span>Get Location</span>
        </button>

        {!isTracking && watchId === null ? (
          <button
            onClick={startTracking}
            className="flex-1 min-w-[120px] px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 flex items-center justify-center space-x-2"
          >
            <Navigation className="w-4 h-4" />
            <span>Start Tracking</span>
          </button>
        ) : (
          <button
            onClick={stopTracking}
            className="flex-1 min-w-[120px] px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 flex items-center justify-center space-x-2"
          >
            <span>Stop Tracking</span>
          </button>
        )}

        <button
          onClick={openInMaps}
          disabled={!location.latitude || !location.longitude}
          className="flex-1 min-w-[120px] px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          <MapPin className="w-4 h-4" />
          <span>Open Maps</span>
        </button>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
        <strong>Note:</strong> Location data is used for field operations and patient visit tracking.
        Enable location permissions for accurate results.
      </div>
    </div>
  );
};

export default LocationTracker;
