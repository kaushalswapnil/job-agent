const API_BASE = process.env.EXPO_PUBLIC_API_URL!

async function authFetch(path: string, token: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  // Onboarding
  saveProfile: (token: string, data: object) =>
    authFetch('/onboarding/profile', token, { method: 'POST', body: JSON.stringify(data) }),

  uploadResume: async (token: string, fileUri: string, fileName: string) => {
    const formData = new FormData()
    formData.append('file', { uri: fileUri, name: fileName, type: 'application/octet-stream' } as any)
    return authFetch('/onboarding/resume', token, {
      method: 'POST',
      body: formData,
      headers: { Authorization: `Bearer ${token}` },
    })
  },

  onboardingStatus: (token: string) => authFetch('/onboarding/status', token),

  // Dashboard
  getStats: (token: string) => authFetch('/dashboard/stats', token),
  getMatches: (token: string, level?: string) =>
    authFetch(`/dashboard/matches${level ? `?level=${level}` : ''}`, token),
  getApplications: (token: string, status?: string) =>
    authFetch(`/dashboard/applications${status ? `?status=${status}` : ''}`, token),
  getApprovals: (token: string) => authFetch('/dashboard/approvals', token),

  // Approvals
  decideApproval: (token: string, id: string, approved: boolean, notes?: string) =>
    authFetch(`/approvals/${id}/decide`, token, {
      method: 'POST',
      body: JSON.stringify({ approved, notes }),
    }),

  // Agents
  runAll: (token: string) => authFetch('/agents/run-all', token, { method: 'POST' }),
  triggerDiscovery: (token: string) => authFetch('/agents/discover', token, { method: 'POST' }),
  triggerMatching: (token: string) => authFetch('/agents/match', token, { method: 'POST' }),
  triggerApplications: (token: string) => authFetch('/agents/process-applications', token, { method: 'POST' }),
}
