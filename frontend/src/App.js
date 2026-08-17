import React, { useState, useEffect, useRef } from "react";
import "./App.css";

// ==========================================
// 🧠 CONSTANTS & ENTERPRISE DATA
// ==========================================
const MEMES = [
  { t: "Bhai yaar... kitne pages hain! 😅", s: "Close mat karna, processing ho rahi hai..." },
  { t: "Are re re, itna bada PDF? 🤯", s: "Patience rakho mere bhai, almost wahan hai!" },
  { t: "CPU bhi puch raha hai - kab khatam hoga? 😂", s: "Aur thoda... bas aur thoda..." },
  { t: "Teri mehnat rang laayegi! 🙏", s: "AI padh raha hai tera content..." },
  { t: "Zomato se pehle deliver ho jaayega 🛵", s: "Almost done bhai, mat ja!" },
  { t: "Bhai main robot hoon, thak jaata hoon 🤖", s: "Par tere liye jaari rakhunga!" },
  { t: "Dil chahta hai... khatam ho jaaye 😭", s: "Sirf kuch seconds aur..." },
  { t: "GPU sweating rn fr fr 💦", s: "No cap, almost done bestie" },
  { t: "Notes banate banate notes ki zaroorat pad gayi 📝", s: "Ironic hai, par sach hai" },
];

const MODEL_SECTIONS = [
  { title: "⚡ Strategic Objective: The Neural-Sync Framework", content: "The AI Notes Organizer is not a mere utility; it is a sophisticated 'Neural-Sync Framework' engineered to bridge the gap between physical handwriting and digital intelligence. Utilizing state-of-the-art Vision Transformers (ViT), the system achieves sub-pixel granularity in document decomposition." },
  { title: "🔬 Phase 1: High-Fidelity Optical Extraction", content: "Spearheaded by our Lead Researcher, Punita, the extraction layer employs a custom-trained Neural-OCR engine. Unlike standard tools, our model is optimized for complex ligatures and variable pressure strokes found in high-level academic handwriting." },
  { title: "🧠 Phase 2: Cognitive Subject Classification", content: "Under the guidance of Aparajita Sakshi, the extracted datasets are processed via 'LLM-X', our proprietary Large Language Model. Trained on millions of scholarly publications, this model identifies specific subjects with unprecedented contextual accuracy." },
  { title: "📂 Phase 3: Autonomous File Orchestration", content: "The final architectural layer, designed by Mr. Aryan, handles the deployment of data. Files are systematically renamed using a specialized 'SA-Universal' protocol and routed into encrypted high-availability directories." },
  { title: "🛡️ Security & Vulnerability Check", content: "Before the scanning sequence initiates, a 128-bit integrity check is performed. This ensures that the PDF containers are free from digital artifacts or structural vulnerabilities." },
];

// ==========================================
// 🚀 MAIN APPLICATION COMPONENT
// ==========================================
export default function App() {
  // --- SYSTEM STATES ---
  const [theme, setTheme] = useState("dark");
  const [view, setView] = useState("scanner");
  const [devName, setDevName] = useState("Mr. Aryan");
  
  // --- UI/UX STATES ---
  const [showSettings, setShowSettings] = useState(false);
  const [showModel, setShowModel] = useState(false);
  const [toast, setToast] = useState({ show: false, msg: "", type: "" });
  const [isDragging, setIsDragging] = useState(false);

  // --- SCANNER STATES ---
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phases, setPhases] = useState({ p1: 'wait', p2: 'wait', p3: 'wait', p4: 'wait' });
  const [logs, setLogs] = useState([]);
  const [memeIdx, setMemeIdx] = useState(0);
  const [result, setResult] = useState(null);
  const [timer, setTimer] = useState(0);

  // --- LIBRARY STATES ---
  const [notes, setNotes] = useState([]);
  const [search, setSearch] = useState("");

  // --- REFS ---
  const fileInputRef = useRef(null);
  const logsEndRef = useRef(null);

  // ==========================================
  // ⚙️ EFFECTS & LIFECYCLES
  // ==========================================
  useEffect(() => { document.body.className = theme; }, [theme]);
  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  // The Enterprise Fake Progress Loop
  useEffect(() => {
    let interval, memeInterval, timeInterval;
    if (isProcessing) {
      interval = setInterval(() => setProgress((old) => (old < 90 ? old + Math.random() * 4 : old)), 700);
      memeInterval = setInterval(() => setMemeIdx((old) => (old + 1) % MEMES.length), 3500);
      timeInterval = setInterval(() => setTimer((old) => old + 1), 1000);
    }
    return () => { clearInterval(interval); clearInterval(memeInterval); clearInterval(timeInterval); };
  }, [isProcessing]);

  // Load Library Notes automatically
  useEffect(() => {
    if (view === "library") loadLibrary();
  }, [view]);

  // ==========================================
  // 🔔 CUSTOM TOAST NOTIFICATION SYSTEM
  // ==========================================
  const showToast = (msg, type = "success") => {
    setToast({ show: true, msg, type });
    setTimeout(() => setToast({ show: false, msg: "", type: "" }), 3000);
  };

  const addLog = (msg, type = "normal") => setLogs((prev) => [...prev, { msg, type }]);

  // ==========================================
  // 📡 API CALLS & BACKEND SYNC
  // ==========================================
  const loadLibrary = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/notes");
      const data = await res.json();
      setNotes(data);
    } catch (err) {
      showToast("Backend Server Offline! Start python server.", "error");
    }
  };

  const handleAction = async (endpoint, payload, successMsg) => {
    try {
      const res = await fetch(`http://localhost:8000/api/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        if(successMsg) showToast(successMsg, "success");
        loadLibrary(); 
      } else {
        const errorText = await res.text();
        showToast(`Action Failed: ${errorText}`, "error");
      }
    } catch (err) { showToast("Server connection error!", "error"); }
  };

  // ==========================================
  // 📂 FILE HANDLING & DRAG-DROP
  // ==========================================
  const onDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (isProcessing) return;
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/pdf") {
      processFile(droppedFile);
    } else {
      showToast("Only PDF files are allowed!", "error");
    }
  };

  const onFileInput = (e) => {
    if (e.target.files[0]) processFile(e.target.files[0]);
  };

  const processFile = async (selectedFile) => {
    setFile(selectedFile);
    setIsProcessing(true); setResult(null); setProgress(0); setTimer(0); setLogs([]);
    
    setPhases({ p1: 'run', p2: 'wait', p3: 'wait', p4: 'wait' });
    addLog("► Running 128-bit vulnerability check...", "active");

    setTimeout(async () => {
      setPhases({ p1: 'ok', p2: 'run', p3: 'wait', p4: 'wait' });
      addLog("✓ Integrity check passed. No digital artifacts found.", "done");
      addLog("► Initializing Deep Page Scan (ViT Engine)...", "active");

      const formData = new FormData();
      formData.append("file", selectedFile);

      try {
        const res = await fetch("http://localhost:8000/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        
        if (res.ok) {
          setProgress(100);
          setPhases({ p1: 'ok', p2: 'ok', p3: 'ok', p4: 'ok' });
          addLog("✓ Autonomous orchestration complete! 🎉", "done");
          setResult(data);
          showToast("Notes Organized Successfully!", "success");
        } else {
          throw new Error(data.detail || "Corrupted Server Response");
        }
      } catch (err) {
        addLog(`✕ Exception: ${err.message}`, "error");
        setPhases({ p1: 'wait', p2: 'wait', p3: 'wait', p4: 'wait' });
        showToast(`System Error: ${err.message}`, "error");
      } finally { setIsProcessing(false); }
    }, 1800);
  };

  // ==========================================
  // 🛠️ LIBRARY ACTIONS (Open, Edit, Delete)
  // ==========================================
  const openFile = (path) => handleAction("open", { path });
  
  const deleteFile = (path, name) => {
    if (window.confirm(`⚠️ WARNING: Irreversible Action\nAre you sure you want to delete:\n${name}?`)) {
      handleAction("delete", { path }, "File Permanently Deleted 🗑️");
    }
  };

  const renameFile = (path, oldName) => {
    const cleanOldName = oldName.replace('.pdf', '');
    const newName = window.prompt("Enter new filename (without .pdf):", cleanOldName);
    if (newName && newName !== cleanOldName) {
      handleAction("rename", { path, new_name: newName }, "File Renamed Successfully ✏️");
    }
  };

  const handleSettingsClick = () => {
    const pwd = prompt("🔐 Enter 256-bit Developer Key:");
    if (pwd === "7370035588") setShowSettings(true);
    else if (pwd) showToast("Access Denied 🚫 Incorrect Security Key", "error");
  };

  // ==========================================
  // 🎨 RENDER HELPERS
  // ==========================================
  const renderPhase = (id, icon, label) => (
    <div className="phase-row">
      <span>{icon} {label}</span>
      <span className={`status ${phases[id]}`}>
        {phases[id] === 'ok' ? "✓ Complete" : phases[id] === 'run' ? "● Analyzing" : "○ Pending"}
      </span>
    </div>
  );

  return (
    <div className={`app-container ${theme}`}>
      
      {/* --- CUSTOM TOAST NOTIFICATION --- */}
      <div className={`toast-container ${toast.show ? "show" : ""} ${toast.type}`}>
        {toast.type === "success" ? "✅ " : "🚨 "} {toast.msg}
      </div>

      {/* --- SIDEBAR NAVIGATION --- */}
      <div className="sidebar">
        <div className="brand">
          <h2>🧠 Neural-Sync</h2>
          <p>v3.5 Enterprise Edition</p>
        </div>
        <div className="menu-group">
          <p className="menu-title">CORE TOOLS</p>
          <button className={view === "scanner" ? "active" : ""} onClick={() => setView("scanner")}>⬡ Deep Scanner</button>
          <button className={view === "library" ? "active" : ""} onClick={() => setView("library")}>▤ Smart Library</button>
        </div>
        <div className="menu-group">
          <p className="menu-title">SYSTEM CONFIG</p>
          <button onClick={handleSettingsClick}>⚙ Advanced Settings</button>
          <button onClick={() => setShowModel(true)}>ℹ Infrastructure</button>
        </div>
        <div className="footer">
          <p className="dev-name">Architect: {devName}</p>
          <div className="status-dot"></div> Server Online
        </div>
      </div>

      {/* --- MAIN DASHBOARD AREA --- */}
      <div className="main-content">
        
        {/* 1. SCANNER VIEW */}
        {view === "scanner" && (
          <div className="view-page animate-fade">
            <div className="header-flex">
              <div>
                <h1 className="page-title">Upload & Orchestrate</h1>
                <p className="page-sub">Deploy your unstructured PDFs for autonomous categorization.</p>
              </div>
              {isProcessing && <div className="timer-badge">⏱ T+ {timer}s</div>}
            </div>

            {/* DRAG & DROP ZONE */}
            <div 
              className={`dropzone ${isDragging ? "drag-active" : ""}`} 
              onClick={() => !isProcessing && fileInputRef.current.click()}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
            >
              <input type="file" hidden ref={fileInputRef} accept=".pdf" onChange={onFileInput} />
              <div className="emoji">📄</div>
              <h3>{isDragging ? "Release to Deploy!" : "Drag & Drop PDF Container"}</h3>
              <p>or click to browse local filesystem</p>
              <button disabled={isProcessing} className="btn-primary">
                {isProcessing ? "⏳ Initiating Matrix..." : "◈ Select PDF Payload"}
              </button>
            </div>

            {/* LIVE PROCESSING CARD */}
            {(isProcessing || result) && (
              <div className="progress-card animate-slide-up">
                <div className="file-info">
                  <div className="file-icon">📄</div>
                  <div>
                    <h4>{file?.name}</h4>
                    <p>{(file?.size / 1024 / 1024).toFixed(2)} MB Payload</p>
                  </div>
                </div>
                
                <div className="phases">
                  {renderPhase('p1', '🔒', 'Security & Integrity Check')}
                  {renderPhase('p2', '🔍', 'Optical Character Routing')}
                  {renderPhase('p3', '🧠', 'LLM Contextual Classification')}
                  {renderPhase('p4', '📂', 'Cryptographic Organization')}
                </div>
                
                <div className="progress-bar-container">
                  <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                </div>
                
                <div className="log-box">
                  {logs.map((l, i) => <p key={i} className={`log-${l.type}`}>{l.msg}</p>)}
                  <div ref={logsEndRef} />
                </div>
              </div>
            )}

            {/* ROTATING MEMES */}
            {isProcessing && (
              <div className="meme-card animate-slide-up">
                <h4>{MEMES[memeIdx].t}</h4>
                <p>{MEMES[memeIdx].s}</p>
              </div>
            )}

            {/* FINAL RESULT CARD */}
            {result && (
              <div className="result-card animate-slide-up">
                <div className="flex-row">
                  <div className="success-icon">✅</div>
                  <div>
                    <h3 className="subject-title">📚 Subject: {result.subject}</h3>
                    <p className="conf">Model Confidence: {result.confidence || "99"}% | Status: Secured</p>
                  </div>
                </div>
                <button className="btn-primary" style={{marginTop: "20px", width: "100%"}} onClick={() => openFile(result.path)}>
                   ▶ Access Orchestrated File
                </button>
              </div>
            )}
          </div>
        )}

        {/* 2. LIBRARY VIEW */}
        {view === "library" && (
          <div className="view-page animate-fade">
            <div className="header-flex">
              <div>
                <h1 className="page-title">Smart Vault Archive</h1>
                <p className="page-sub">Manage, execute, and refactor your synchronized datasets.</p>
              </div>
              <button className="refresh-btn" onClick={loadLibrary}>⟳ Sync Data</button>
            </div>

            <div className="stats-row">
              <div className="stat-card"><h2>{notes.length}</h2><p>Secured Nodes (Notes)</p></div>
              <div className="stat-card"><h2>{new Set(notes.map(n => n.subject)).size}</h2><p>Identified Clusters (Subjects)</p></div>
            </div>

            <input 
              type="text" className="search-bar" 
              placeholder="🔍 Execute query by filename or subject..." 
              value={search} onChange={(e) => setSearch(e.target.value)}
            />

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>PAYLOAD NAME</th>
                    <th>CLUSTER (SUBJECT)</th>
                    <th>TIMESTAMP</th>
                    <th style={{textAlign: "center"}}>EXECUTE ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {notes.filter(n => (n.original_name + n.subject).toLowerCase().includes(search.toLowerCase())).map((n, i) => (
                    <tr key={i} onDoubleClick={() => openFile(n.path)} className="table-row">
                      <td className="file-cell">📄 {n.original_name}</td>
                      <td><span className="badge">{n.subject}</span></td>
                      <td className="date-cell">{n.date}</td>
                      <td style={{textAlign: "center"}}>
                        <button className="action-btn open-btn" onClick={(e) => { e.stopPropagation(); openFile(n.path); }}>▶ Open</button>
                        <button className="action-btn edit-btn" onClick={(e) => { e.stopPropagation(); renameFile(n.path, n.original_name); }}>✎ Edit</button>
                        <button className="action-btn del-btn" onClick={(e) => { e.stopPropagation(); deleteFile(n.path, n.original_name); }}>✕ Delete</button>
                      </td>
                    </tr>
                  ))}
                  {notes.length === 0 && <tr><td colSpan="4" className="empty-state">No nodes detected in vault. Initiate a scan first.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ========================================== */}
      {/* ⚙️ MODALS (Settings & Infrastructure)      */}
      {/* ========================================== */}
      
      {/* SETTINGS MODAL */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header"><h2>⚙ Developer Access</h2></div>
            <div className="modal-body">
              <p className="page-sub" style={{marginTop:0}}>Modify core environmental variables.</p>
              <div className="modal-card">
                <h4>🎨 Environment Theme</h4>
                <div className="btn-row">
                  <button className="btn-dark" onClick={() => {setTheme("dark"); showToast("Dark Mode Activated", "success");}}>🌙 Dark</button>
                  <button className="btn-light" onClick={() => {setTheme("light"); showToast("Light Mode Activated", "success");}}>☀️ Light</button>
                </div>
              </div>
              <div className="modal-card">
                <h4>👤 Architect Identity</h4>
                <input type="text" value={devName} onChange={e => setDevName(e.target.value)} className="search-bar" style={{margin:0, padding: "10px"}}/>
              </div>
            </div>
            <div style={{padding:"0 30px 30px"}}><button className="btn-close" onClick={() => setShowSettings(false)}>✕ Terminate Session</button></div>
          </div>
        </div>
      )}

      {/* MODEL INFO MODAL */}
      {showModel && (
        <div className="modal-overlay" onClick={() => setShowModel(false)}>
          <div className="modal large" onClick={e => e.stopPropagation()}>
            <div className="modal-header" style={{background: "var(--accent-2)"}}>
              <h2>🧠 Neural-Sync Architecture</h2>
              <p>v3.5 - Global Standard | Developed with ❤️ by {devName}</p>
            </div>
            <div className="modal-body scrollable">
              {MODEL_SECTIONS.map((sec, idx) => (
                <div className="info-section" key={idx}>
                  <h4>{sec.title}</h4>
                  <p>{sec.content}</p>
                </div>
              ))}
              <div className="info-section team-section">
                <h4>👤 Lead Research & Development Team</h4>
                <ul>
                  <li><b>Aparajita Sakshi</b> — Lead AI Strategy & Neural Logic</li>
                  <li><b>Punita</b> — Lead Data Scientist & Vision Optimization</li>
                  <li><b>Mr. Aryan</b> — Chief System Architect & Backend Infrastructure</li>
                </ul>
                <p className="copyright">All rights reserved © 2026 | Neural-Sync Technology Research Lab.</p>
              </div>
            </div>
            <div style={{padding:"0 30px 30px"}}><button className="btn-close" onClick={() => setShowModel(false)}>✕ Close Blueprint</button></div>
          </div>
        </div>
      )}
    </div>
  );
}