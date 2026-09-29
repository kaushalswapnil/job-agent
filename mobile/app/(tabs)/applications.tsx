import { useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, RefreshControl, TouchableOpacity, Linking } from 'react-native'
import { useAuthStore } from '../store/auth'
import { api } from '../lib/api'

const STATUS_COLOR: Record<string, string> = {
  APPLICATION_SUBMITTED: '#10b981',
  PENDING_APPROVAL: '#f59e0b',
  RESUME_GENERATED: '#6366f1',
  INTERVIEW_REQUESTED: '#06b6d4',
  INTERVIEW_SCHEDULED: '#84cc16',
  REJECTED: '#ef4444',
  OFFER: '#f97316',
  WITHDRAWN: '#6b7280',
}

export default function ApplicationsScreen() {
  const { session } = useAuthStore()
  const [apps, setApps] = useState<any[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    if (!session) return
    try {
      const data = await api.getApplications(session.access_token)
      setApps(data)
    } catch (e) { console.error(e) }
  }

  useEffect(() => { load() }, [session])
  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false) }

  return (
    <View style={s.container}>
      <Text style={s.header}>Applications ({apps.length})</Text>
      <FlatList
        data={apps}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
        renderItem={({ item }) => {
          const color = STATUS_COLOR[item.status] || '#64748b'
          return (
            <TouchableOpacity style={s.card} onPress={() => Linking.openURL(item.job_url)}>
              <View style={s.cardTop}>
                <View style={[s.statusBadge, { backgroundColor: color + '22' }]}>
                  <Text style={[s.statusText, { color }]}>{item.status.replace(/_/g, ' ')}</Text>
                </View>
                <Text style={s.score}>{item.job_match_score?.toFixed(0) ?? '—'}%</Text>
              </View>
              <Text style={s.title}>{item.role}</Text>
              <Text style={s.company}>{item.company} · {item.country || 'Unknown'}</Text>
              {item.next_action && <Text style={s.nextAction}>→ {item.next_action}</Text>}
              {item.interview_date && (
                <Text style={s.interview}>📅 Interview: {new Date(item.interview_date).toLocaleDateString()}</Text>
              )}
            </TouchableOpacity>
          )
        }}
        ListEmptyComponent={<Text style={s.empty}>No applications yet. Approve matches to start applying.</Text>}
      />
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: { fontSize: 18, fontWeight: '700', color: '#f1f5f9', padding: 16 },
  card: { margin: 8, marginHorizontal: 12, backgroundColor: '#1e293b', borderRadius: 14, padding: 16 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  statusText: { fontSize: 11, fontWeight: '700' },
  score: { fontSize: 18, fontWeight: '800', color: '#6366f1' },
  title: { fontSize: 15, fontWeight: '700', color: '#f1f5f9', marginBottom: 2 },
  company: { fontSize: 13, color: '#94a3b8', marginBottom: 6 },
  nextAction: { fontSize: 12, color: '#6366f1', marginTop: 4 },
  interview: { fontSize: 12, color: '#10b981', marginTop: 4 },
  empty: { textAlign: 'center', color: '#64748b', marginTop: 60, fontSize: 14, paddingHorizontal: 32 },
})
