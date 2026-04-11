import React, { useState } from 'react';
import TodoList from './TodoList.jsx';
import AddTaskForm from './AddTaskForm.jsx';
import FilterControls from './FilterControls.jsx';

const App = () => {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');

  const addTask = (description) => {
    if (description.trim()) {
      setTasks([...tasks, { id: Date.now(), description, completed: false }]);
    }
  };

  const deleteTask = (id) => {
    setTasks(tasks.filter(task => task.id !== id));
  };

  const toggleComplete = (id) => {
    setTasks(tasks.map(task => task.id === id ? { ...task, completed: !task.completed } : task));
  };

  const filteredTasks = tasks.filter(task => {
    if (filter === 'all') return true;
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return false;
  });

  return (
    <div>
      <h1>Todo App</h1>
      <AddTaskForm onAdd={addTask} />
      <FilterControls onFilterChange={setFilter} filter={filter} />
      <TodoList tasks={filteredTasks} onDelete={deleteTask} onComplete={toggleComplete} />
    </div>
  );
};

export default App;