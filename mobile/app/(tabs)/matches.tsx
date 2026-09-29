import { useEffect, useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Linking, RefreshControl } from 'react-native'
import { useAuthStore } from '../store/auth'
import { api } from '../lib/api'

const LEVEL_COLOR: Record<string, string> = {
  HIGH_MATCH: '#10b981',
  MEDIUM_MATCH: '#f59e0b',
  LOW_MATCH: '#ef4444',
  DO_NOT_APPLY: '#6b7280',
}

export default function MatchesScreen() {
  const { session } = useAuthStore()
  const [matches, setMatches] = useState<any[]>([])
  const [filter, setFilter] = useState<string | undefined>('HIGH_MATCH')
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    if (!session) return
    try {
      const data = await api.getMatches(session.access_token, filter)
      setMatches(data)
    } catch (e) { console.error(e) }
  }

  useEffect(() => { load() }, [session, filter])
  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false) }

  const FilterBtn = ({ level, label }: { level: string | undefined; label: string }) => (
    <TouchableOpacity
      style={[s.filterBtn, filter === level && s.filterBtnActive]}
      onPress={() => setFilter(level)}
    >
      <Text style={[s.filterText, filter === level && s.filterTextActive]}>{label}</Text>
    </TouchableOpacity>
  )

  return (
    <View style={s.container}>
      <View style={s.filters}>
        <FilterBtn level="HIGH_MATCH" label="High" />
        <FilterBtn level="MEDIUM_MATCH" label="Medium" />
        <FilterBtn level={undefined} label="All" />
      </View>

      <FlatList
        data={matches}
        keyExtractor={(item) => item.job_id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.card} onPress={() => Linking.openURL(item.url)}>
            <View style={s.cardHeader}>
              <View style={[s.badge, { backgroundColor: LEVEL_COLOR[item.match_level] + '22' }]}>
                <Text style={[s.badgeText, { color: LEVEL_COLOR[item.match_level] }]}>
                  {item.overall_score?.toFixed(0)}%
                </Text>
              </View>
              <Text style={s.remote}>{item.remote_type}</Text>
            </View>
            <Text style={s.title}>{item.title}</Text>
            <Text style={s.company}>{item.company}</Text>
            <Text style={s.location}>{item.country || 'Unknown'} · {item.visa_sponsorship}</Text>
            <View style={s.scores}>
              {[
                { label: 'AI', val: item.ai_score },
                { label: 'Java', val: item.java_score },
                { label: 'FE', val: item.frontend_score },
                { label: 'Cloud', val: item.cloud_score },
              ].map(({ label, val }) => (
                <View key={label} style={s.scoreChip}>
                  <Text style={s.scoreLabel}>{label}</Text>
                  <Text style={s.scoreVal}>{val?.toFixed(0) ?? '—'}</Text>
                </View>
              ))}
            </View>
            {item.explanation?.summary && (
              <Text style={s.summary} numberOfLines={2}>{item.explanation.summary}</Text>
            )}
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={s.empty}>No matches yet. Run the pipeline from Dashboard.</Text>}
      />
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  filters: { flexDirection: 'row', padding: 12, gap: 8 },
  filterBtn: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, backgroundColor: '#1e293b' },
  filterBtnActive: { backgroundColor: '#6366f1' },
  filterText: { color: '#94a3b8', fontSize: 13, fontWeight: '600' },
  filterTextActive: { color: '#fff' },
  card: { margin: 8, marginHorizontal: 12, backgroundColor: '#1e293b', borderRadius: 14, padding: 16 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  badgeText: { fontWeight: '800', fontSize: 14 },
  remote: { color: '#64748b', fontSize: 12, alignSelf: 'center' },
  title: { fontSize: 16, fontWeight: '700', color: '#f1f5f9', marginBottom: 2 },
  company: { fontSize: 14, color: '#94a3b8', marginBottom: 4 },
  location: { fontSize: 12, color: '#64748b', marginBottom: 10 },
  scores: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  scoreChip: { backgroundColor: '#0f172a', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4, alignItems: 'center' },
  scoreLabel: { fontSize: 10, color: '#64748b' },
  scoreVal: { fontSize: 13, fontWeight: '700', color: '#6366f1' },
  summary: { fontSize: 12, color: '#64748b', lineHeight: 18 },
  empty: { textAlign: 'center', color: '#64748b', marginTop: 60, fontSize: 14 },
})
