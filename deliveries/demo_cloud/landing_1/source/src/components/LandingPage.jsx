import React from 'react';
import Header from './Header.jsx';
import Hero from './Hero.jsx';
import MenuHighlights from './MenuHighlights.jsx';
import About from './About.jsx';
import Contact from './Contact.jsx';
import Footer from './Footer.jsx';

function LandingPage() {
  return (
    <div className="landing-page">
      <Header />
      <main>
        <Hero />
        <MenuHighlights />
        <About />
        <Contact />
      </main>
      <Footer />
    </div>
  );
}

export default LandingPage;
