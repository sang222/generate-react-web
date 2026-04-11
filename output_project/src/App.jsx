import React, { useState } from 'react';
import TodoList from './TodoList.jsx';
import TodoForm from './TodoForm.jsx';
import FilterDropdown from './FilterDropdown.jsx';

const App = () => {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');

  const addTask = (task) => {
    if (task.trim() !== '') {
      setTasks([...tasks, { text: task, completed: false }]);
    }
  };

  const deleteTask = (index) => {
    if (tasks.length > 1) {
      setTasks(tasks.filter((_, i) => i !== index));
    }
  };

  const toggleCompletion = (index) => {
    setTasks(tasks.map((task, i) => (
      i === index ? { ...task, completed: !task.completed } : task
    )));
  };

  const filteredTasks = tasks.filter(task => {
    if (filter === 'all') return true;
    return filter === 'completed' ? task.completed : !task.completed;
  });

  return (
    <div className="app">
      <h1>Todo App</h1>
      <FilterDropdown filter={filter} setFilter={setFilter} />
      <TodoForm addTask={addTask} />
      <TodoList tasks={filteredTasks} deleteTask={deleteTask} toggleCompletion={toggleCompletion} />
    </div>
  );
};

export default App;