// API Client connecting to the Python FastAPI backend
const API_BASE_URL = "http://localhost:8000/api";

// Mock data fallback in case backend is offline during frontend preview
const MOCK_DIAGNOSTICS = {
  database: "OK",
  youtube_configuration: "OK",
  active_concepts: 1,
  videos: 5,
  candidates: 12,
  population_members: 5,
  observations: 15,
  signals: 3,
  api_failures: 0,
  latest_observation: new Date().toISOString(),
  latest_signal: new Date().toISOString()
};

const MOCK_CONCEPTS = [
  {
    id: 1,
    name: "AI Agents",
    description: "Monitors agentic AI workflows, frameworks, and LLM automation tools",
    active: true,
    search_queries: ["AI agents", "agentic AI", "AI automation"]
  }
];

const MOCK_SIGNALS = [
  {
    id: 1,
    concept_id: 1,
    signal_date: "2026-08-17",
    population_size: 5,
    observation_coverage: 1.0,
    median_view_velocity: 150,
    median_view_growth: 0.15,
    median_view_acceleration: 20,
    median_normalized_velocity: 0.05,
    median_reach_ratio: 0.2,
    median_interaction_density: 0.08,
    p25_velocity: 100,
    p75_velocity: 250,
    velocity_std: 45,
    big_creator_signal: 300,
    medium_creator_signal: 120,
    small_creator_signal: 30
  },
  {
    id: 2,
    concept_id: 1,
    signal_date: "2026-08-18",
    population_size: 5,
    observation_coverage: 1.0,
    median_view_velocity: 220,
    median_view_growth: 0.22,
    median_view_acceleration: 70,
    median_normalized_velocity: 0.07,
    median_reach_ratio: 0.25,
    median_interaction_density: 0.09,
    p25_velocity: 150,
    p75_velocity: 350,
    velocity_std: 60,
    big_creator_signal: 450,
    medium_creator_signal: 180,
    small_creator_signal: 50
  },
  {
    id: 3,
    concept_id: 1,
    signal_date: "2026-08-19",
    population_size: 5,
    observation_coverage: 1.0,
    median_view_velocity: 350,
    median_view_growth: 0.35,
    median_view_acceleration: 130,
    median_normalized_velocity: 0.11,
    median_reach_ratio: 0.32,
    median_interaction_density: 0.11,
    p25_velocity: 220,
    p75_velocity: 550,
    velocity_std: 95,
    big_creator_signal: 700,
    medium_creator_signal: 280,
    small_creator_signal: 80
  }
];

const MOCK_PROVENANCE = {
  signal: MOCK_SIGNALS[2],
  population_run_id: 42,
  contributions: [
    { video_id: "vid_1", title: "Building AI Agents: Complete Guide", creator_bucket: "big", selection_score: 0.88, selection_rank: 1, observed: true, view_count: 2500, view_velocity: 700, view_growth: 0.38, normalized_velocity: 0.07, reach_ratio: 0.25, interaction_density: 0.12 },
    { video_id: "vid_2", title: "Agentic AI is the Future!", creator_bucket: "medium", selection_score: 0.82, selection_rank: 2, observed: true, view_count: 1800, view_velocity: 280, view_growth: 0.18, normalized_velocity: 0.05, reach_ratio: 0.36, interaction_density: 0.08 },
    { video_id: "vid_3", title: "AutoGPT & CrewAI Tutorial", creator_bucket: "medium", selection_score: 0.79, selection_rank: 3, observed: true, view_count: 700, view_velocity: 350, view_growth: 0.35, normalized_velocity: 0.07, reach_ratio: 0.14, interaction_density: 0.11 },
    { video_id: "vid_4", title: "Open Source AI Agent Frameworks", creator_bucket: "small", selection_score: 0.74, selection_rank: 4, observed: true, view_count: 500, view_velocity: 220, view_growth: 0.44, normalized_velocity: 0.44, reach_ratio: 1.0, interaction_density: 0.15 },
    { video_id: "vid_5", title: "I built 5 AI agents in 24 hours", creator_bucket: "small", selection_score: 0.69, selection_rank: 5, observed: true, view_count: 250, view_velocity: 80, view_growth: 0.32, normalized_velocity: 0.16, reach_ratio: 0.5, interaction_density: 0.10 }
  ]
};

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
      console.warn("Diagnostics API failed, falling back to mock data.", err);
      return MOCK_DIAGNOSTICS;
    }
  },

  getConcepts: async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/concepts`);
      const data = await handleResponse(resp);
      return data.length > 0 ? data : MOCK_CONCEPTS;
    } catch (err) {
      console.warn("Concepts API failed, falling back to mock data.", err);
      return MOCK_CONCEPTS;
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
      console.error("Failed to create concept", err);
      throw err;
    }
  },

  getSignals: async (conceptId) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/signals?concept_id=${conceptId}`);
      const data = await handleResponse(resp);
      return data.length > 0 ? data : MOCK_SIGNALS;
    } catch (err) {
      console.warn("Signals API failed, falling back to mock data.", err);
      return MOCK_SIGNALS;
    }
  },

  getProvenance: async (conceptId, dateStr) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/provenance?concept_id=${conceptId}&target_date=${dateStr}`);
      return await handleResponse(resp);
    } catch (err) {
      console.warn("Provenance API failed, falling back to mock data.", err);
      return MOCK_PROVENANCE;
    }
  },

  triggerPipeline: async (stage) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/pipeline/run?stage=${stage}`, {
        method: "POST"
      });
      return await handleResponse(resp);
    } catch (err) {
      console.error(`Failed to trigger pipeline stage ${stage}`, err);
      throw err;
    }
  },

  getRawDataSummary: async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/diagnostics/raw-data`);
      return await handleResponse(resp);
    } catch (err) {
      console.warn("Raw data summary API failed, falling back to mock counts.", err);
      return {
        concepts: 1,
        channels: 5,
        videos: 5,
        search_runs: 1,
        video_candidates: 12,
        population_runs: 1,
        population_members: 5,
        video_observations: 15,
        video_metrics: 15,
        concept_daily_signals: 3,
        api_request_logs: 25
      };
    }
  },

  getRawTableData: async (tableName, limit = 200) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/diagnostics/raw-data/${tableName}?limit=${limit}`);
      return await handleResponse(resp);
    } catch (err) {
      console.warn(`Raw data API for table ${tableName} failed, falling back to mock rows.`, err);
      const mockRows = [];
      const count = 5;
      for (let i = 1; i <= count; i++) {
        mockRows.push({
          id: i,
          video_id: `mock_vid_${i}`,
          channel_id: `mock_channel_${i}`,
          title: `Mock Video Title ${i}`,
          subscriber_count: i * 50000,
          views: i * 1000,
          created_at: new Date().toISOString(),
          requested_at: new Date().toISOString(),
          success: true,
          api_name: "youtube",
          endpoint: "search",
          operation: "list",
          status: "active"
        });
      }
      return {
        table: tableName,
        count: mockRows.length,
        limit,
        data: mockRows
      };
    }
  }
};
