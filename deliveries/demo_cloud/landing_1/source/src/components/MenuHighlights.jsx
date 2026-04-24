import React from 'react';
import './MenuHighlights.css';

const menuItems = [
  {
    id: 1,
    name: 'Signature Espresso',
    description: 'Rich, bold espresso with notes of dark chocolate and caramel.',
    price: '$3.50',
    image: 'https://placehold.co/400x300/6f4e37/ffffff?text=Espresso'
  },
  {
    id: 2,
    name: 'Caramel Macchiato',
    description: 'Layered espresso drink with vanilla, milk, and caramel drizzle.',
    price: '$5.25',
    image: 'https://placehold.co/400x300/c9a66e/ffffff?text=Macchiato'
  },
  {
    id: 3,
    name: 'Cold Brew',
    description: 'Smooth, low-acid cold brew steeped for 20 hours.',
    price: '$4.75',
    image: 'https://placehold.co/400x300/3d2b1f/ffffff?text=Cold+Brew'
  }
];

function MenuHighlights() {
  return (
    <section id="menu" className="menu-highlights">
      <div className="container">
        <h2 className="section-title">Featured Drinks</h2>
        <div className="menu-grid">
          {menuItems.map(item => (
            <div key={item.id} className="menu-card">
              <div className="menu-image">
                <img src={item.image} alt={item.name} />
              </div>
              <div className="menu-content">
                <h3 className="menu-name">{item.name}</h3>
                <p className="menu-description">{item.description}</p>
                <span className="menu-price">{item.price}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default MenuHighlights;
