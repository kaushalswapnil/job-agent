import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform } from 'react-native'
import { useRouter } from 'expo-router'
import { useAuthStore } from '../store/auth'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const { signInWithEmail, signUpWithEmail } = useAuthStore()
  const router = useRouter()

  const handleSubmit = async () => {
    if (!email || !password) return Alert.alert('Error', 'Email and password are required')
    setLoading(true)
    try {
      if (isSignUp) {
        if (!fullName) return Alert.alert('Error', 'Full name is required')
        await signUpWithEmail(email, password, fullName)
        Alert.alert('Check your email', 'We sent you a confirmation link.')
      } else {
        await signInWithEmail(email, password)
      }
    } catch (e: any) {
      Alert.alert('Error', e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={s.card}>
        <Text style={s.title}>🤖 Job Agent</Text>
        <Text style={s.subtitle}>AI-powered job search, running 24/7</Text>

        {isSignUp && (
          <TextInput style={s.input} placeholder="Full Name" value={fullName}
            onChangeText={setFullName} placeholderTextColor="#94a3b8" />
        )}
        <TextInput style={s.input} placeholder="Email" value={email}
          onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none"
          placeholderTextColor="#94a3b8" />
        <TextInput style={s.input} placeholder="Password" value={password}
          onChangeText={setPassword} secureTextEntry placeholderTextColor="#94a3b8" />

        <TouchableOpacity style={[s.btn, loading && s.btnDisabled]} onPress={handleSubmit} disabled={loading}>
          <Text style={s.btnText}>{loading ? 'Please wait...' : isSignUp ? 'Create Account' : 'Sign In'}</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setIsSignUp(!isSignUp)}>
          <Text style={s.toggle}>
            {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a', justifyContent: 'center', padding: 24 },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 24 },
  title: { fontSize: 28, fontWeight: '700', color: '#f1f5f9', textAlign: 'center', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', marginBottom: 32 },
  input: { backgroundColor: '#0f172a', color: '#f1f5f9', borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 16 },
  btn: { backgroundColor: '#6366f1', borderRadius: 10, padding: 16, alignItems: 'center', marginTop: 8 },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  toggle: { color: '#6366f1', textAlign: 'center', marginTop: 16, fontSize: 14 },
})
