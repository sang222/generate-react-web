import React from 'react';

const TodoList = ({ tasks, deleteTask, toggleCompletion }) => {
  return (
    <ul>
      {tasks.map((task, index) => (
        <li key={index} className={task.completed ? 'completed' : ''}>
          <input type="checkbox" checked={task.completed} onChange={() => toggleCompletion(index)} />
          {task.text}
          <button onClick={() => deleteTask(index)}>Delete</button>
        </li>
      ))}
    </ul>
  );
};

export default TodoList;