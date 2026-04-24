import React from 'react';
import Hero from './components/Hero.jsx';
import Details from './components/Details.jsx';
import Footer from './components/Footer.jsx';
import './App.css';

function App() {
  return (
    <div className="app">
      <Hero />
      <Details />
      <Footer />
    </div>
  );
}

export default App;
