import { useEffect } from 'react'
import { Stack, useRouter, useSegments } from 'expo-router'
import { supabase } from './lib/supabase'
import { useAuthStore } from './store/auth'

export default function RootLayout() {
  const { session, setSession } = useAuthStore()
  const segments = useSegments()
  const router = useRouter()

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    const inAuthGroup = segments[0] === '(auth)'
    if (!session && !inAuthGroup) {
      router.replace('/(auth)/login')
    } else if (session && inAuthGroup) {
      router.replace('/(tabs)/dashboard')
    }
  }, [session, segments])

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  )
}
