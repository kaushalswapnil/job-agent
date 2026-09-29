import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{
      tabBarStyle: { backgroundColor: '#1e293b', borderTopColor: '#334155' },
      tabBarActiveTintColor: '#6366f1',
      tabBarInactiveTintColor: '#64748b',
      headerStyle: { backgroundColor: '#0f172a' },
      headerTintColor: '#f1f5f9',
    }}>
      <Tabs.Screen name="dashboard" options={{
        title: 'Dashboard',
        tabBarIcon: ({ color, size }) => <Ionicons name="grid-outline" size={size} color={color} />,
      }} />
      <Tabs.Screen name="matches" options={{
        title: 'Matches',
        tabBarIcon: ({ color, size }) => <Ionicons name="star-outline" size={size} color={color} />,
      }} />
      <Tabs.Screen name="approvals" options={{
        title: 'Approvals',
        tabBarIcon: ({ color, size }) => <Ionicons name="checkmark-circle-outline" size={size} color={color} />,
      }} />
      <Tabs.Screen name="applications" options={{
        title: 'Applications',
        tabBarIcon: ({ color, size }) => <Ionicons name="briefcase-outline" size={size} color={color} />,
      }} />
      <Tabs.Screen name="onboarding" options={{
        title: 'Setup',
        tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" size={size} color={color} />,
      }} />
    </Tabs>
  )
}
