import React, { useEffect, useState } from "react";

function ViewNotes() {
  const [notes, setNotes] = useState([]);

  useEffect(() => {
    const fetchNotes = async () => {
      try {
        // Python server se data mangwa rahe hain
        const response = await fetch("http://localhost:8000/api/notes");
        const data = await response.json();
        setNotes(data);
      } catch (err) {
        console.error("Error fetching notes:", err);
      }
    };

    fetchNotes();
  }, []);

  return (
    <div>
      <h2>Library & History 📚</h2>

      <div className="grid">
        {notes.map((n, i) => (
          <div key={i} className="card">
            <h3>{n.subject}</h3>
            <p><strong>File:</strong> {n.original_name}</p>
            <p style={{fontSize: "12px", color: "gray", marginTop: "10px"}}>
              Scanned on: {n.date}
            </p>
          </div>
        ))}
        {notes.length === 0 && <p>No notes found. Upload something first!</p>}
      </div>
    </div>
  );
}

export default ViewNotes;