import { createClient } from '@supabase/supabase-js'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { Platform } from 'react-native'
import 'react-native-url-polyfill/auto'

const SUPABASE_URL = 'https://ngrudtbshliklqaznloi.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ncnVkdGJzaGxpa2xxYXpubG9pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM0MDUxMzAsImV4cCI6MjA5ODk4MTEzMH0.n5B5AV_8hvLQRayF3g1MhAbGqsSh4TAu6EiY_xrd4K4'

// Fix for Node.js 20 WebSocket issue in Expo web
const getWebSocketImpl = () => {
  if (Platform.OS === 'web' && typeof WebSocket !== 'undefined') {
    return WebSocket
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require('ws')
  } catch {
    return WebSocket
  }
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: Platform.OS === 'web' ? undefined : AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: Platform.OS === 'web',
  },
  realtime: {
    transport: getWebSocketImpl(),
    params: { eventsPerSecond: 2 },
  },
})
