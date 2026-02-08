import React from 'react';

const EmergencyContact: React.FC = () => {
  const callEmergency = () => {
    window.location.href = 'tel:911';
  };

  const sendEmergencyAlert = () => {
    // In a real app, this would send an alert to emergency contacts
    alert('Emergency alert sent to designated contacts');
  };

  return (
    <div className="p-4 border rounded-lg bg-red-50">
      <h3 className="text-lg font-semibold mb-2 text-red-800">Emergency Contact Protocols</h3>
      <p className="text-sm text-gray-600 mb-4">
        Use these buttons in case of medical emergencies or critical situations.
      </p>
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={callEmergency}
          className="px-6 py-3 bg-red-600 text-white rounded font-bold hover:bg-red-700"
        >
          🚨 Call 911
        </button>
        <button
          onClick={sendEmergencyAlert}
          className="px-6 py-3 bg-orange-600 text-white rounded font-bold hover:bg-orange-700"
        >
          📢 Send Alert
        </button>
      </div>
      <div className="mt-4 p-3 bg-yellow-100 rounded">
        <h4 className="font-semibold text-yellow-800">Emergency Protocol:</h4>
        <ol className="text-sm text-yellow-700 mt-1 list-decimal list-inside">
          <li>Assess the situation immediately</li>
          <li>Call 911 if there's imminent danger</li>
          <li>Send emergency alert to team</li>
          <li>Follow established emergency procedures</li>
        </ol>
      </div>
    </div>
  );
};

export default EmergencyContact;
