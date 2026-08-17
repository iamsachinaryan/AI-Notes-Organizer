import React, { useState } from "react";

function Upload() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!file) return alert("Bhai, pehle PDF file select karo!");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Python Backend ko file bhej rahe hain
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.status === "duplicate") {
        alert(`Duplicate Found 🧠\nYe file pehle se '${result.data.subject}' mein organized hai.`);
      } else if (result.status === "success") {
        alert(`Magic Done! 🚀\nFile Organized under: ${result.subject}`);
      } else {
        alert("Error: " + result.detail);
      }
    } catch (err) {
      console.error(err);
      alert("Server error! Kya tumhara Python backend chalu hai?");
    }
    setLoading(false);
  };

  return (
    <div className="card form-card">
      <h2>Upload Notes</h2>
      <p>Select PDF for Neural-Sync AI Scanning</p>

      <input 
        type="file" 
        accept="application/pdf" 
        onChange={(e) => setFile(e.target.files[0])} 
      />

      <button onClick={handleSubmit} disabled={loading} style={{marginTop: "15px"}}>
        {loading ? "AI is Scanning... ⏳" : "Upload & Organize 🚀"}
      </button>
    </div>
  );
}

export default Upload;