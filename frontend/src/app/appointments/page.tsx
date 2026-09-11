"use client";
import React, { useState, useEffect } from 'react';

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal aur Booking ke states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [bookingDate, setBookingDate] = useState("");

  const availableDoctors = [
    { id: "DOC-101", name: "Dr. Rajesh Sharma", specialty: "Cardiologist", experience: "15 Years", rating: "4.9/5", fee: "₹800" },
    { id: "DOC-102", name: "Dr. Sneha Gupta", specialty: "Endocrinologist", experience: "10 Years", rating: "4.8/5", fee: "₹600" },
    { id: "DOC-103", name: "Dr. Amit Verma", specialty: "General Physician", experience: "8 Years", rating: "4.7/5", fee: "₹500" },
    { id: "DOC-104", name: "Dr. Priya Desai", specialty: "Dermatologist", experience: "12 Years", rating: "4.9/5", fee: "₹700" }
  ];

  useEffect(() => {
    const fetchAppointments = async () => {
      try {
        let token = localStorage.getItem('token') || localStorage.getItem('access_token'); 
        if (token && token.startsWith('"') && token.endsWith('"')) {
          token = token.slice(1, -1);
        }

        if (!token) {
          setLoading(false);
          return; 
        }

        const response = await fetch('http://localhost:8000/api/v1/appointments', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
          }
        });
        
        if (response.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('access_token');
          setLoading(false);
          return;
        }

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        setAppointments(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAppointments();
  }, []);

  // Button Click Handler
  const handleBookClick = (doctor) => {
    setSelectedDoctor(doctor);
    setIsModalOpen(true);
  };

  // Booking Confirm Handler (Demo)
  const confirmBooking = () => {
    if (!bookingDate) {
      alert("Please select a date first!");
      return;
    }
    alert(`Appointment Confirmed for ${selectedDoctor.name} on ${bookingDate}!`);
    setIsModalOpen(false);
    setBookingDate("");
  };

  return (
    <div style={{ padding: '30px', color: '#e2e8f0', fontFamily: 'sans-serif', maxWidth: '1000px', margin: '0 auto', position: 'relative' }}>
      <h1 style={{ fontSize: '28px', borderBottom: '2px solid #334155', paddingBottom: '10px', marginBottom: '20px' }}>
        📅 My Appointments
      </h1>
      
      {loading && <p style={{ color: '#38bdf8' }}>Loading your appointments...</p>}
      
      {error && (
        <div style={{ backgroundColor: '#7f1d1d', color: '#fca5a5', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
          <p><strong>⚠️ Error:</strong> {error}</p>
        </div>
      )}
      
      {/* Existing Appointments List */}
      {!loading && !error && appointments.length > 0 && (
        <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', marginTop: '20px', backgroundColor: '#1e293b', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ backgroundColor: '#0f172a' }}>
              <th style={{ padding: '15px', borderBottom: '1px solid #334155' }}>Apt ID</th>
              <th style={{ padding: '15px', borderBottom: '1px solid #334155' }}>Doctor ID</th>
              <th style={{ padding: '15px', borderBottom: '1px solid #334155' }}>Status</th>
              <th style={{ padding: '15px', borderBottom: '1px solid #334155' }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((apt, index) => (
              <tr key={index} style={{ borderBottom: '1px solid #334155' }}>
                <td style={{ padding: '15px' }}>{apt.id || 'N/A'}</td>
                <td style={{ padding: '15px' }}>{apt.doctor_id || 'N/A'}</td>
                <td style={{ padding: '15px' }}><span style={{ backgroundColor: '#065f46', color: '#6ee7b7', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}>{apt.status || 'SCHEDULED'}</span></td>
                <td style={{ padding: '15px' }}>{apt.scheduled_at || 'Pending'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Available Doctors List */}
      {!loading && !error && appointments.length === 0 && (
        <div style={{ marginTop: '10px' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#94a3b8' }}>No Previous Appointments</h3>
            <p style={{ margin: '0' }}>You haven't booked any appointments yet. Choose a doctor from below to get started.</p>
          </div>

          <h2 style={{ fontSize: '24px', marginBottom: '20px', color: '#38bdf8' }}>🩺 Available Doctors to Book</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
            {availableDoctors.map((doc) => (
              <div key={doc.id} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{ margin: '0 0 5px 0', fontSize: '20px', color: '#f8fafc' }}>{doc.name}</h3>
                  <span style={{ backgroundColor: '#0f172a', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' }}>{doc.id}</span>
                </div>
                <p style={{ color: '#10b981', margin: '0 0 15px 0', fontWeight: 'bold' }}>{doc.specialty}</p>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#cbd5e1', marginBottom: '20px' }}>
                  <span>⭐ {doc.rating}</span>
                  <span>⏳ {doc.experience}</span>
                  <span>💰 {doc.fee}</span>
                </div>
                
                {/* YAHAN ONCLICK ADD KIYA HAI */}
                <button 
                  onClick={() => handleBookClick(doc)}
                  style={{ width: '100%', padding: '10px', backgroundColor: '#0ea5e9', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer' }}
                >
                  Book Appointment
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL POPUP UI */}
      {isModalOpen && selectedDoctor && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#1e293b', padding: '30px', borderRadius: '10px', width: '400px', maxWidth: '90%', border: '1px solid #475569' }}>
            <h2 style={{ marginTop: 0, color: '#f8fafc' }}>Book Appointment</h2>
            <p style={{ color: '#94a3b8' }}>Doctor: <strong style={{ color: 'white' }}>{selectedDoctor.name}</strong> ({selectedDoctor.specialty})</p>
            <p style={{ color: '#94a3b8' }}>Fee: <strong style={{ color: 'white' }}>{selectedDoctor.fee}</strong></p>
            
            <div style={{ margin: '20px 0' }}>
              <label style={{ display: 'block', marginBottom: '8px', color: '#e2e8f0' }}>Select Date & Time:</label>
              <input 
                type="datetime-local" 
                value={bookingDate}
                onChange={(e) => setBookingDate(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #334155', backgroundColor: '#0f172a', color: 'white', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
              <button 
                onClick={() => setIsModalOpen(false)} 
                style={{ padding: '10px 20px', backgroundColor: '#475569', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button 
                onClick={confirmBooking} 
                style={{ padding: '10px 20px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}