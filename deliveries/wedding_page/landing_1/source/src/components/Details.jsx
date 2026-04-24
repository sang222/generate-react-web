import React from 'react';
import './Details.css';

function Details() {
  return (
    <section className="details">
      <div className="details-content">
        <h2 className="details-heading">The Celebration</h2>
        <div className="detail-item">
          <span className="detail-label">When</span>
          <span className="detail-value">4:00 PM - 10:00 PM</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Where</span>
          <span className="detail-value">The Rosewood Estate</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Address</span>
          <span className="detail-value">123 Garden Lane, Portland, OR</span>
        </div>
      </div>
    </section>
  );
}

export default Details;
