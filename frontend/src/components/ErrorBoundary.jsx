import React from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            margin: 20,
            padding: 24,
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #dadce0",
            boxShadow: "0 1px 4px rgba(60,64,67,0.1)",
            color: "#202124",
            fontFamily: "Roboto, Google Sans, Inter, sans-serif",
            maxWidth: 800,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "#fce8e6",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle size={22} color="#d93025" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, color: "#d93025", fontWeight: 700 }}>
                {this.props.title || "Something went wrong in this view"}
              </h3>
              <p style={{ margin: "2px 0 0 0", fontSize: 13, color: "#5f6368" }}>
                An unexpected interface error was prevented from crashing the application.
              </p>
            </div>
          </div>

          <div
            style={{
              background: "#f8f9fa",
              border: "1px solid #dadce0",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
              fontSize: 12,
              fontFamily: "monospace",
              color: "#3c4043",
              overflowX: "auto",
              maxHeight: 180,
            }}
          >
            {this.state.error?.toString() || "Unknown runtime exception"}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={this.handleReset}
              className="pill-btn"
              style={{
                background: "#1a73e8",
                color: "#ffffff",
                border: "none",
                padding: "8px 18px",
                borderRadius: 20,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <RefreshCw size={14} />
              <span>Try Again</span>
            </button>
            <button
              onClick={this.handleReload}
              className="pill-btn"
              style={{
                background: "#ffffff",
                color: "#5f6368",
                border: "1px solid #dadce0",
                padding: "8px 18px",
                borderRadius: 20,
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
