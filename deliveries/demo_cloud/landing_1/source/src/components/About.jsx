import React from 'react';
import './About.css';

function About() {
  return (
    <section id="about" className="about">
      <div className="container about-content">
        <div className="about-image">
          <img src="https://placehold.co/600x400/6f4e37/ffffff?text=Our+Story" alt="Our coffee shop interior" />
        </div>
        <div className="about-text">
          <h2 className="section-heading">Our Story</h2>
          <p>
            Founded in 2020, Brew & Bean began with a simple mission: to create
            exceptional coffee experiences in a warm, welcoming environment.
          </p>
          <p>
            We source our beans directly from sustainable farms, roast them in
            small batches, and craft each drink with care. Our baristas are
            passionate about their craft and love sharing their knowledge with
            our customers.
          </p>
          <p>
            Whether you're looking for your morning pick-me-up or a quiet place
            to relax, we invite you to join us at Brew & Bean.
          </p>
        </div>
      </div>
    </section>
  );
}

export default About;
