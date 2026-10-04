// API Client connecting strictly to the Python FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function handleResponse(response) {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `API error: ${response.status}`);
  }
  return response.json();
}

export const apiService = {
  getDiagnostics: async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/diagnostics`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Diagnostics API call failed:", err);
      return {
        database: "DISCONNECTED",
        youtube_configuration: "UNKNOWN",
        active_concepts: 0,
        videos: 0,
        signals: 0,
        api_failures: 0,
        latest_signal: null
      };
    }
  },

  getConcepts: async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/concepts`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Concepts API call failed:", err);
      return [];
    }
  },

  createConcept: async (name, queries, description) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/concepts?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description || "")}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(queries)
      });
      return await handleResponse(resp);
    } catch (err) {
      console.error("Failed to create concept:", err);
      throw err;
    }
  },

  getSignals: async (conceptId) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/signals?concept_id=${conceptId}`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Signals API call failed:", err);
      return [];
    }
  },

  getLatestEntries: async (limit = 20) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/latest-entries?limit=${limit}`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Latest entries API call failed:", err);
      return [];
    }
  },

  getProvenance: async (conceptId, dateStr) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/provenance?concept_id=${conceptId}&target_date=${dateStr}`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Provenance API call failed:", err);
      return null;
    }
  },

  triggerPipeline: async (stage) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/pipeline/run?stage=${stage}`, {
        method: "POST"
      });
      return await handleResponse(resp);
    } catch (err) {
      console.error(`Failed to trigger pipeline stage '${stage}':`, err);
      throw err;
    }
  },

  getRawDataSummary: async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/diagnostics/raw-data`);
      return await handleResponse(resp);
    } catch (err) {
      console.error("Raw data summary API call failed:", err);
      return {
        concepts: 0,
        concept_daily_signals: 0,
        api_request_logs: 0
      };
    }
  },

  getRawTableData: async (tableName, limit = 200) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/diagnostics/raw-data/${tableName}?limit=${limit}`);
      return await handleResponse(resp);
    } catch (err) {
      console.error(`Raw table data API call for table '${tableName}' failed:`, err);
      return {
        table: tableName,
        count: 0,
        limit,
        data: []
      };
    }
  }
};
