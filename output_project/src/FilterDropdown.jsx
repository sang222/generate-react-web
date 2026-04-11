import React from 'react';

const FilterDropdown = ({ filter, setFilter }) => {
  return (
    <select value={filter} onChange={(e) => setFilter(e.target.value)}>
      <option value="all">All</option>
      <option value="completed">Completed</option>
      <option value="incomplete">Incomplete</option>
    </select>
  );
};

export default FilterDropdown;