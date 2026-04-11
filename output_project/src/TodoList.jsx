import React from 'react';
import TodoItem from './TodoItem.jsx';

const TodoList = ({ tasks, onDelete, onComplete }) => {
  return (
    <ul>
      {tasks.map(task => (
        <li key={task.id} onClick={() => onComplete(task.id)} style={{ textDecoration: task.completed ? 'line-through' : 'none', cursor: 'pointer' }}>
          {task.description}
          <button onClick={(e) => { e.stopPropagation(); onDelete(task.id); }}>Delete</button>
        </li>
      ))}
    </ul>
  );
};

export default TodoList;