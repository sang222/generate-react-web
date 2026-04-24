import React from 'react';
import './Hero.css';

function Hero() {
  return (
    <section id="hero" className="hero">
      <div className="container hero-content">
        <div className="hero-text">
          <h1 className="hero-title">Crafted Coffee, Warm Moments</h1>
          <p className="hero-subtitle">
            Experience the perfect blend of artisanal coffee and cozy atmosphere.
            Handcrafted drinks made with passion and precision.
          </p>
          <a href="#menu" className="btn hero-btn">Order Now</a>
        </div>
      </div>
    </section>
  );
}

export default Hero;
