import { useEffect, useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl, Alert } from 'react-native'
import { useAuthStore } from '../store/auth'
import { api } from '../lib/api'

interface Stats {
  total_jobs_discovered: number
  jobs_evaluated: number
  high_match_jobs: number
  applications_submitted: number
  pending_approval: number
  recruiter_responses: number
  interviews: number
  rejections: number
  offers: number
}

export default function DashboardScreen() {
  const { session } = useAuthStore()
  const [stats, setStats] = useState<Stats | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [running, setRunning] = useState(false)

  const load = async () => {
    if (!session) return
    try {
      const data = await api.getStats(session.access_token)
      setStats(data)
    } catch (e: any) {
      console.error(e.message)
    }
  }

  const runAll = async () => {
    if (!session) return
    setRunning(true)
    try {
      await api.runAll(session.access_token)
      Alert.alert('Started', 'Discovery → Matching → Application pipeline is running in the background.')
    } catch (e: any) {
      Alert.alert('Error', e.message)
    } finally {
      setRunning(false)
    }
  }

  useEffect(() => { load() }, [session])

  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false) }

  const StatCard = ({ label, value, color = '#6366f1' }: { label: string; value: number; color?: string }) => (
    <View style={[s.statCard, { borderLeftColor: color }]}>
      <Text style={[s.statValue, { color }]}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  )

  return (
    <ScrollView style={s.container} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}>
      <View style={s.header}>
        <Text style={s.title}>🤖 Job Agent</Text>
        <Text style={s.subtitle}>Running 24/7 in the cloud</Text>
      </View>

      <TouchableOpacity style={[s.runBtn, running && s.runBtnDisabled]} onPress={runAll} disabled={running}>
        <Text style={s.runBtnText}>{running ? '⏳ Running...' : '▶ Run Full Pipeline Now'}</Text>
      </TouchableOpacity>

      {stats && (
        <View style={s.grid}>
          <StatCard label="Jobs Discovered" value={stats.total_jobs_discovered} color="#6366f1" />
          <StatCard label="Evaluated" value={stats.jobs_evaluated} color="#8b5cf6" />
          <StatCard label="High Matches" value={stats.high_match_jobs} color="#10b981" />
          <StatCard label="Applied" value={stats.applications_submitted} color="#3b82f6" />
          <StatCard label="Pending Approval" value={stats.pending_approval} color="#f59e0b" />
          <StatCard label="Recruiter Responses" value={stats.recruiter_responses} color="#06b6d4" />
          <StatCard label="Interviews" value={stats.interviews} color="#84cc16" />
          <StatCard label="Offers" value={stats.offers} color="#f97316" />
        </View>
      )}

      {!stats && (
        <View style={s.empty}>
          <Text style={s.emptyText}>Complete setup to start your job search →</Text>
        </View>
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: { padding: 24, paddingBottom: 8 },
  title: { fontSize: 24, fontWeight: '700', color: '#f1f5f9' },
  subtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  runBtn: { margin: 16, backgroundColor: '#6366f1', borderRadius: 12, padding: 16, alignItems: 'center' },
  runBtnDisabled: { opacity: 0.6 },
  runBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', padding: 8 },
  statCard: { width: '46%', margin: '2%', backgroundColor: '#1e293b', borderRadius: 12, padding: 16, borderLeftWidth: 3 },
  statValue: { fontSize: 28, fontWeight: '800' },
  statLabel: { fontSize: 12, color: '#94a3b8', marginTop: 4 },
  empty: { margin: 24, padding: 24, backgroundColor: '#1e293b', borderRadius: 12, alignItems: 'center' },
  emptyText: { color: '#94a3b8', fontSize: 14, textAlign: 'center' },
})
