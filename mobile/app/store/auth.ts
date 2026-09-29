import { create } from 'zustand'
import { supabase } from '../lib/supabase'
import { Session } from '@supabase/supabase-js'

interface AuthState {
  session: Session | null
  loading: boolean
  setSession: (s: Session | null) => void
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (email: string, password: string, fullName: string) => Promise<void>
  signOut: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  loading: true,

  setSession: (session) => set({ session, loading: false }),

  signInWithEmail: async (email, password) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  },

  signUpWithEmail: async (email, password, fullName) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    })
    if (error) throw error
  },

  signOut: async () => {
    await supabase.auth.signOut()
    set({ session: null })
  },
}))
