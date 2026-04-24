import React from 'react';
import './Contact.css';

function Contact() {
  return (
    <section id="contact" className="contact">
      <div className="container">
        <h2 className="section-title">Visit Us</h2>
        <div className="contact-grid">
          <div className="contact-info">
            <div className="contact-item">
              <h3 className="contact-heading">Location</h3>
              <p>123 Coffee Lane</p>
              <p>Seattle, WA 98101</p>
            </div>
            <div className="contact-item">
              <h3 className="contact-heading">Hours</h3>
              <p>Monday - Friday: 7am - 8pm</p>
              <p>Saturday: 8am - 9pm</p>
              <p>Sunday: 9am - 7pm</p>
            </div>
            <div className="contact-item">
              <h3 className="contact-heading">Contact</h3>
              <p>hello@brewandbean.com</p>
              <p>(555) 123-4567</p>
            </div>
          </div>
          <div className="contact-map">
            <iframe
              title="Map"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d126688.4063635092!2d-122.3364724!3d47.6062098!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x5490407a1b8b9e77%3A0x59bdb2a0b8a0e7a7!2sSeattle%2C%20WA!5e0!3m2!1sen!2sus!4v1704067200000!5m2!1sen!2sus"
              width="100%"
              height="300"
              style={{ border: 0, borderRadius: 'var(--radius-lg)' }}
              allowfullscreen=""
              loading="lazy"
              referrerpolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Contact;
