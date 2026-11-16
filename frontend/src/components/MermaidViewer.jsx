import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Copy, Check, Download, ZoomIn, ZoomOut, RotateCcw, ExternalLink, Code } from "lucide-react";

// Initialize mermaid with Google Material Design 3 light theme
mermaid.initialize({
  startOnLoad: false,
  theme: "neutral",
  themeVariables: {
    darkMode: false,
    background: "#ffffff",
    primaryColor: "#e8f0fe",
    primaryTextColor: "#202124",
    primaryBorderColor: "#1a73e8",
    lineColor: "#80868b",
    secondaryColor: "#f1f3f4",
    tertiaryColor: "#f8f9fa",
    fontFamily: "Roboto, Google Sans, Inter, system-ui, sans-serif",
    fontSize: "13px",
  },
  securityLevel: "loose",
  flowchart: {
    htmlLabels: true,
    curve: "basis",
  },
  sequence: {
    diagramMarginX: 30,
    diagramMarginY: 20,
    actorMargin: 50,
    width: 140,
    height: 55,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
  },
});

export default function MermaidViewer({ chart, title = "Architecture Diagram", diagramType = "C4 / Architecture" }) {
  const containerRef = useRef(null);
  const [svgContent, setSvgContent] = useState("");
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!chart || !chart.trim()) {
        setSvgContent("");
        return;
      }
      try {
        setError(null);
        const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(uniqueId, chart);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err) {
        console.error("Mermaid render error:", err);
        if (isMounted) {
          setError(err?.message || "Failed to render Mermaid diagram");
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = () => {
    if (!chart) return;
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSVG = () => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.toLowerCase().replace(/[^a-z0-9]/g, "_")}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleOpenDrawIo = () => {
    alert(
      "To open in Draw.io (diagrams.net):\n\n1. The Mermaid code has been copied to your clipboard.\n2. Open diagrams.net / draw.io\n3. Click: Arrange > Insert > Advanced > Mermaid\n4. Paste the code and click Insert!\n\nIt will render as an editable C4 enterprise architecture diagram."
    );
    handleCopy();
  };

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #dadce0",
        borderRadius: 8,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        boxShadow: "none",
      }}
    >
      {/* Diagram Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 16px",
          background: "#f8f9fa",
          borderBottom: "1px solid #dadce0",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              padding: "3px 10px",
              borderRadius: 16,
              background: "#e8f0fe",
              color: "#1a73e8",
              border: "1px solid #dadce0",
            }}
          >
            {diagramType}
          </span>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#202124" }}>{title}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {/* Zoom Controls */}
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
            title="Zoom Out"
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              color: "#5f6368",
              borderRadius: 24,
              padding: "5px 8px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ZoomOut size={13} />
          </button>
          <span style={{ fontSize: 11, color: "#5f6368", minWidth: 38, textAlign: "center", fontWeight: 500 }}>
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
            title="Zoom In"
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              color: "#5f6368",
              borderRadius: 24,
              padding: "5px 8px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ZoomIn size={13} />
          </button>
          <button
            onClick={() => setZoom(1)}
            title="Reset Zoom"
            style={{
              background: "#ffffff",
              border: "1px solid #dadce0",
              color: "#5f6368",
              borderRadius: 24,
              padding: "5px 8px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <RotateCcw size={13} />
          </button>

          <div style={{ width: 1, height: 18, background: "#dadce0", margin: "0 4px" }} />

          {/* Toggle Raw Code */}
          <button
            onClick={() => setShowCode(!showCode)}
            style={{
              background: showCode ? "#e8f0fe" : "#ffffff",
              color: showCode ? "#1a73e8" : "#3c4043",
              border: showCode ? "1px solid #1a73e8" : "1px solid #dadce0",
              borderRadius: 24,
              padding: "5px 12px",
              fontSize: 11.5,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Code size={13} />
            <span>{showCode ? "Hide Syntax" : "View Syntax"}</span>
          </button>

          {/* Copy Code */}
          <button
            onClick={handleCopy}
            title="Copy Mermaid Code (can paste into Draw.io or Markdown)"
            style={{
              background: copied ? "#e6f4ea" : "#ffffff",
              color: copied ? "#137333" : "#3c4043",
              border: copied ? "1px solid #ceead6" : "1px solid #dadce0",
              borderRadius: 24,
              padding: "5px 12px",
              fontSize: 11.5,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            <span>{copied ? "Copied" : "Copy Code"}</span>
          </button>

          {/* Draw.io Direct Helper */}
          <button
            onClick={handleOpenDrawIo}
            title="Copy & instructions for Draw.io (diagrams.net)"
            style={{
              background: "#ffffff",
              color: "#1a73e8",
              border: "1px solid #dadce0",
              borderRadius: 24,
              padding: "5px 12px",
              fontSize: 11.5,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <ExternalLink size={13} />
            <span>Draw.io</span>
          </button>

          {/* Download SVG */}
          <button
            onClick={handleDownloadSVG}
            disabled={!svgContent}
            title="Download Vector SVG"
            style={{
              background: svgContent ? "#1a73e8" : "#f1f3f4",
              color: svgContent ? "#ffffff" : "#9aa0a6",
              border: svgContent ? "1px solid #1a73e8" : "1px solid #dadce0",
              borderRadius: 24,
              padding: "5px 12px",
              fontSize: 11.5,
              fontWeight: 600,
              cursor: svgContent ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Download size={13} />
            <span>SVG</span>
          </button>
        </div>
      </div>

      {/* Raw Syntax Drawer */}
      {showCode && (
        <div
          style={{
            background: "#f8f9fa",
            borderBottom: "1px solid #dadce0",
            padding: 12,
            maxHeight: 180,
            overflowY: "auto",
          }}
        >
          <pre
            style={{
              margin: 0,
              color: "#202124",
              fontFamily: "Roboto Mono, monospace",
              fontSize: 11.5,
              lineHeight: 1.45,
            }}
          >
            {chart}
          </pre>
        </div>
      )}

      {/* Render Canvas */}
      <div
        ref={containerRef}
        style={{
          padding: 24,
          minHeight: 380,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          overflow: "auto",
          background: "#ffffff",
        }}
      >
        {error ? (
          <div style={{ textAlign: "center", color: "#d93025", padding: 20 }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Syntax Rendering Notice</div>
            <div style={{ fontSize: 12, color: "#5f6368", maxWidth: 500, margin: "0 auto" }}>{error}</div>
            <pre
              style={{
                marginTop: 12,
                background: "#fce8e6",
                border: "1px solid #fad2cf",
                padding: 10,
                borderRadius: 8,
                fontSize: 11,
                color: "#c5221f",
                textAlign: "left",
                maxHeight: 150,
                overflowY: "auto",
              }}
            >
              {chart}
            </pre>
          </div>
        ) : svgContent ? (
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: "center center",
              transition: "transform 0.15s ease",
              width: "100%",
              display: "flex",
              justifyContent: "center",
            }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        ) : (
          <div style={{ color: "#5f6368", fontSize: 13 }}>Preparing architectural visualization...</div>
        )}
      </div>
    </div>
  );
}
