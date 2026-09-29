import { useEffect, useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Alert, RefreshControl, Linking } from 'react-native'
import { useAuthStore } from '../store/auth'
import { api } from '../lib/api'

export default function ApprovalsScreen() {
  const { session } = useAuthStore()
  const [approvals, setApprovals] = useState<any[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    if (!session) return
    try {
      const data = await api.getApprovals(session.access_token)
      setApprovals(data)
    } catch (e) { console.error(e) }
  }

  useEffect(() => { load() }, [session])
  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false) }

  const decide = async (id: string, approved: boolean, company: string) => {
    Alert.alert(
      approved ? 'Confirm Application' : 'Skip Application',
      approved
        ? `Apply to ${company}?`
        : `Skip ${company}? This will mark it as withdrawn.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: approved ? 'Yes, Apply' : 'Yes, Skip',
          style: approved ? 'default' : 'destructive',
          onPress: async () => {
            try {
              await api.decideApproval(session!.access_token, id, approved)
              setApprovals(prev => prev.filter(a => a.id !== id))
            } catch (e: any) {
              Alert.alert('Error', e.message)
            }
          },
        },
      ]
    )
  }

  return (
    <View style={s.container}>
      <Text style={s.header}>⚡ Pending Approvals ({approvals.length})</Text>
      <FlatList
        data={approvals}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
        renderItem={({ item }) => (
          <View style={s.card}>
            <View style={s.cardTop}>
              <Text style={s.score}>{item.match_score?.toFixed(0) ?? '—'}%</Text>
              <TouchableOpacity onPress={() => Linking.openURL(item.job_url)}>
                <Text style={s.link}>View Job ↗</Text>
              </TouchableOpacity>
            </View>
            <Text style={s.title}>{item.role}</Text>
            <Text style={s.company}>{item.company} · {item.country || 'Unknown'}</Text>

            <View style={s.questions}>
              {(item.questions || []).map((q: any, i: number) => (
                <View key={i} style={s.question}>
                  <Text style={s.questionText}>❓ {q.question}</Text>
                  {q.recommended && (
                    <Text style={s.recommended}>💡 {q.recommended}</Text>
                  )}
                </View>
              ))}
            </View>

            <View style={s.actions}>
              <TouchableOpacity style={s.skipBtn} onPress={() => decide(item.id, false, item.company)}>
                <Text style={s.skipText}>Skip</Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.approveBtn} onPress={() => decide(item.id, true, item.company)}>
                <Text style={s.approveText}>✓ Approve & Apply</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyText}>No pending approvals 🎉</Text>
            <Text style={s.emptySubtext}>Run the pipeline to discover and match new jobs.</Text>
          </View>
        }
      />
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: { fontSize: 18, fontWeight: '700', color: '#f1f5f9', padding: 16 },
  card: { margin: 8, marginHorizontal: 12, backgroundColor: '#1e293b', borderRadius: 14, padding: 16 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  score: { fontSize: 22, fontWeight: '800', color: '#10b981' },
  link: { color: '#6366f1', fontSize: 13 },
  title: { fontSize: 16, fontWeight: '700', color: '#f1f5f9', marginBottom: 2 },
  company: { fontSize: 13, color: '#94a3b8', marginBottom: 12 },
  questions: { gap: 8, marginBottom: 16 },
  question: { backgroundColor: '#0f172a', borderRadius: 8, padding: 10 },
  questionText: { color: '#e2e8f0', fontSize: 13, lineHeight: 18 },
  recommended: { color: '#6366f1', fontSize: 12, marginTop: 4 },
  actions: { flexDirection: 'row', gap: 10 },
  skipBtn: { flex: 1, padding: 12, borderRadius: 10, borderWidth: 1, borderColor: '#334155', alignItems: 'center' },
  skipText: { color: '#94a3b8', fontWeight: '600' },
  approveBtn: { flex: 2, padding: 12, borderRadius: 10, backgroundColor: '#6366f1', alignItems: 'center' },
  approveText: { color: '#fff', fontWeight: '700' },
  empty: { alignItems: 'center', marginTop: 80 },
  emptyText: { color: '#f1f5f9', fontSize: 18, fontWeight: '700' },
  emptySubtext: { color: '#64748b', fontSize: 13, marginTop: 8, textAlign: 'center', paddingHorizontal: 32 },
})
