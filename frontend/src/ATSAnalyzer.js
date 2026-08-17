import React, { useState } from "react";

export default function ATSAnalyzer() {
  const [jobDesc, setJobDesc] = useState("");
  const [skills, setSkills] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    if (!jobDesc || !skills) {
      alert("Bhai, Job Description aur Skills dono daal!");
      return;
    }
    
    setLoading(true);
    setResult(null);

    try {
      // Backend ke Ghost-Worker ko call kar raha hai
      const res = await fetch("http://localhost:8000/api/ats-analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDesc,
          current_skills: skills,
        }),
      });
      
      const responseData = await res.json();
      
      if (responseData.status === "success") {
        setResult(responseData.data);
      } else {
        alert("System Error: " + responseData.message);
      }
    } catch (error) {
      alert("Server Offline! Backend chalu kar bhai.");
    } finally {
      setLoading(false);
    }
  };

  // Cyberpunk Theme Styles
  const theme = {
    bg: "#05050A",
    surface: "rgba(25, 25, 35, 0.6)",
    border: "rgba(255, 255, 255, 0.1)",
    cyan: "#00F0FF",
    purple: "#8B5CF6",
    red: "#FF003C",
    green: "#10B981",
    textMain: "#FFFFFF",
    textMuted: "#94A3B8"
  };

  return (
    <div style={{ padding: "40px", color: theme.textMain, fontFamily: "Inter, sans-serif" }}>
      
      {/* 🔴 HEADER SECTION */}
      <div style={{ marginBottom: "40px" }}>
        <span style={{ 
          display: "inline-block", padding: "6px 12px", borderRadius: "20px", 
          background: "rgba(255,0,60,0.1)", border: `1px solid ${theme.red}`, 
          color: theme.red, fontSize: "12px", fontWeight: "bold", letterSpacing: "2px",
          marginBottom: "15px", textTransform: "uppercase"
        }}>
          Phase 2: Employment
        </span>
        <h1 style={{ fontSize: "42px", margin: "0 0 10px 0", fontFamily: "'Space Grotesk', sans-serif" }}>
          ATS <span style={{ color: theme.cyan }}>Skill Analyzer</span>
        </h1>
        <p style={{ color: theme.textMuted, fontSize: "18px", margin: 0 }}>
          Defeat the corporate filter. Map your skills against real JD requirements.
        </p>
      </div>

      {/* 🔴 MAIN GRID (2 Columns) */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "40px" }}>
        
        {/* 🟢 LEFT COLUMN: INPUTS */}
        <div style={{ 
          background: theme.surface, backdropFilter: "blur(20px)", 
          padding: "30px", borderRadius: "16px", border: `1px solid ${theme.border}`,
          boxShadow: "0 20px 40px rgba(0,0,0,0.4)"
        }}>
          <h3 style={{ color: theme.purple, margin: "0 0 25px 0", fontSize: "24px" }}>Data Ingestion</h3>
          
          <label style={{ display: "block", color: theme.textMuted, fontSize: "13px", fontWeight: "bold", marginBottom: "8px", letterSpacing: "1px" }}>
            TARGET JOB DESCRIPTION
          </label>
          <textarea 
            style={{ 
              width: "100%", height: "180px", background: "rgba(0,0,0,0.3)", 
              border: `1px solid ${theme.border}`, borderRadius: "8px", color: "#fff", 
              padding: "15px", fontSize: "15px", resize: "none", marginBottom: "25px",
              outline: "none"
            }}
            placeholder="Paste the company's job description here..."
            value={jobDesc}
            onChange={(e) => setJobDesc(e.target.value)}
          />

          <label style={{ display: "block", color: theme.textMuted, fontSize: "13px", fontWeight: "bold", marginBottom: "8px", letterSpacing: "1px" }}>
            YOUR CURRENT SKILLS
          </label>
          <textarea 
            style={{ 
              width: "100%", height: "120px", background: "rgba(0,0,0,0.3)", 
              border: `1px solid ${theme.border}`, borderRadius: "8px", color: "#fff", 
              padding: "15px", fontSize: "15px", resize: "none", marginBottom: "30px",
              outline: "none"
            }}
            placeholder="E.g., React, Python, Basic SQL, HTML/CSS..."
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
          />

          <button 
            onClick={handleAnalyze}
            disabled={loading}
            style={{ 
              width: "100%", padding: "16px", background: loading ? "#333" : theme.cyan, 
              color: loading ? "#fff" : "#000", border: "none", borderRadius: "8px", 
              fontSize: "16px", fontWeight: "bold", cursor: loading ? "not-allowed" : "pointer",
              transition: "0.3s", boxShadow: loading ? "none" : `0 0 20px rgba(0, 240, 255, 0.4)`
            }}
          >
            {loading ? "⏳ Ghost-Worker Processing..." : "🚀 Initiate Deep Scan"}
          </button>
        </div>

        {/* 🟢 RIGHT COLUMN: OUTPUTS */}
        <div style={{ 
          background: theme.surface, backdropFilter: "blur(20px)", 
          padding: "40px", borderRadius: "16px", border: `1px solid ${theme.border}`,
          display: "flex", flexDirection: "column", justifyContent: "center",
          boxShadow: "0 20px 40px rgba(0,0,0,0.4)", minHeight: "500px"
        }}>
          
          {/* WAITING STATE */}
          {!result && !loading && (
            <div style={{ textAlign: "center", color: theme.textMuted }}>
              <i className="fa-solid fa-radar" style={{ fontSize: "60px", opacity: 0.2, marginBottom: "20px" }}></i>
              <h2 style={{ color: "#fff", marginBottom: "10px" }}>Waiting for Payload...</h2>
              <p>Enter JD and skills to begin architectural scan.</p>
            </div>
          )}

          {/* LOADING STATE */}
          {loading && (
            <div style={{ textAlign: "center", color: theme.cyan }}>
              <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: "60px", marginBottom: "20px" }}></i>
              <h2 style={{ marginBottom: "10px" }}>Bypassing Corporate Firewall...</h2>
              <p style={{ color: theme.textMuted }}>Querying Gemini LLM-X Architecture...</p>
            </div>
          )}

          {/* RESULT STATE */}
          {result && !loading && (
            <div style={{ animation: "fadeIn 0.5s ease-in" }}>
              
              {/* Score Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: `1px solid ${theme.border}`, paddingBottom: "25px", marginBottom: "25px" }}>
                <div>
                  <h3 style={{ margin: "0 0 10px 0", color: "#fff", fontSize: "24px" }}>Match Analysis</h3>
                  <p style={{ margin: 0, color: theme.textMuted, fontSize: "16px" }}>
                    Verdict: <strong style={{ color: result.ats_score >= 70 ? theme.green : theme.red }}>{result.verdict}</strong>
                  </p>
                </div>
                <div style={{ textAlign: "center", background: "rgba(0,0,0,0.4)", padding: "15px 25px", borderRadius: "12px", border: `1px solid ${result.ats_score >= 70 ? theme.green : theme.red}` }}>
                  <h1 style={{ margin: 0, fontSize: "48px", color: result.ats_score >= 70 ? theme.green : theme.red }}>
                    {result.ats_score}%
                  </h1>
                  <span style={{ fontSize: "12px", color: theme.textMuted, letterSpacing: "2px" }}>ATS SCORE</span>
                </div>
              </div>

              {/* Missing Keywords */}
              <h4 style={{ color: theme.red, margin: "0 0 15px 0", fontSize: "18px" }}>🚨 Missing Keywords (Red Flags)</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "35px" }}>
                {result.missing_keywords && result.missing_keywords.length > 0 ? (
                  result.missing_keywords.map((kw, i) => (
                    <span key={i} style={{ 
                      background: "rgba(255,0,60,0.1)", color: theme.red, padding: "8px 16px", 
                      borderRadius: "20px", fontSize: "14px", fontWeight: "bold", border: `1px solid ${theme.red}` 
                    }}>
                      {kw}
                    </span>
                  ))
                ) : (
                  <span style={{ color: theme.green, fontWeight: "bold" }}>No major missing keywords! Great job.</span>
                )}
              </div>

              {/* Actionable Roadmap */}
              <h4 style={{ color: theme.cyan, margin: "0 0 15px 0", fontSize: "18px" }}>🗺️ Actionable Roadmap</h4>
              <ul style={{ color: "#E2E8F0", fontSize: "15px", paddingLeft: "20px", lineHeight: "1.8", margin: 0 }}>
                {result.roadmap && result.roadmap.map((step, i) => (
                  <li key={i} style={{ marginBottom: "10px" }}>{step}</li>
                ))}
              </ul>

            </div>
          )}
        </div>

      </div>
    </div>
  );
}