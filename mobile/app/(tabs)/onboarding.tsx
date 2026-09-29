import { useState } from 'react'
import { View, Text, ScrollView, TextInput, TouchableOpacity, StyleSheet, Switch, Platform } from 'react-native'
import { useAuthStore } from '../store/auth'
import { api } from '../lib/api'

const DEFAULT_ROLES = [
  'AI Engineer', 'Generative AI Engineer', 'LLM Engineer', 'RAG Engineer',
  'Senior Java Developer', 'Java Full Stack Developer', 'Full Stack Engineer',
  'Senior Software Engineer', 'Backend Engineer',
]

const DEFAULT_SKILLS = [
  'Java', 'Spring Boot', 'Python', 'React', 'Angular', 'TypeScript',
  'AWS', 'Docker', 'Kubernetes', 'LangChain', 'RAG', 'LLMs',
  'Amazon Bedrock', 'OpenAI APIs', 'Vector Databases', 'Microservices',
]

export default function OnboardingScreen() {
  const { session, signOut } = useAuthStore()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    linkedin_url: '',
    naukri_url: '',
    github_url: '',
    current_city: 'Bangalore',
    current_country: 'India',
    experience_years: '7',
    ai_years: '3',
    java_years: '6',
    frontend_years: '4',
    cloud_years: '4',
    professional_summary: '',
    notification_email: '',
    selectedRoles: [...DEFAULT_ROLES],
    selectedSkills: [...DEFAULT_SKILLS],
    remote_preferred: true,
    open_to_relocation: true,
  })

  const update = (field: string, value: any) => setForm(f => ({ ...f, [field]: value }))

  const toggleItem = (key: 'selectedRoles' | 'selectedSkills', item: string) => {
    setForm(f => ({
      ...f,
      [key]: f[key].includes(item) ? f[key].filter(i => i !== item) : [...f[key], item],
    }))
  }

  const saveProfile = async () => {
    if (!session) return
    if (!form.full_name) { setError('Full name is required'); return }
    setError('')
    setSaving(true)
    try {
      await api.saveProfile(session.access_token, {
        full_name: form.full_name,
        phone: form.phone,
        linkedin_url: form.linkedin_url,
        naukri_url: form.naukri_url,
        github_url: form.github_url,
        current_city: form.current_city,
        current_country: form.current_country,
        experience_years: parseInt(form.experience_years) || 0,
        ai_years: parseInt(form.ai_years) || 0,
        java_years: parseInt(form.java_years) || 0,
        frontend_years: parseInt(form.frontend_years) || 0,
        cloud_years: parseInt(form.cloud_years) || 0,
        professional_summary: form.professional_summary,
        notification_email: form.notification_email,
        target_roles: form.selectedRoles,
        skills: form.selectedSkills,
        job_prefs: { remote_preference: form.remote_preferred ? 'preferred' : 'open_to', auto_apply_threshold: 80 },
        work_authorization: { india: 'authorized', usa: 'requires_sponsorship', europe: 'requires_sponsorship', remote: 'authorized' },
        location_prefs: { india: { enabled: true }, europe: { enabled: true }, remote_worldwide: { enabled: true } },
        salary_prefs: { india: { currency: 'INR', minimum: 2500000, target: 3500000 } },
      })
      setStep(2)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  // Web file upload using native input
  const pickAndUploadResume = () => {
    if (!session) return
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.docx,.txt'
    input.onchange = async (e: any) => {
      const file = e.target.files[0]
      if (!file) return
      setSaving(true)
      setError('')
      try {
        const formData = new FormData()
        formData.append('file', file)
        const res = await fetch(`${process.env.EXPO_PUBLIC_API_URL}/onboarding/resume`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${session.access_token}` },
          body: formData,
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Upload failed')
        }
        setSuccess('Resume uploaded! Job search will start automatically.')
        setStep(3)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setSaving(false)
      }
    }
    input.click()
  }

  if (step === 3) {
    return (
      <View style={[s.container, { justifyContent: 'center', alignItems: 'center', padding: 32 }]}>
        <Text style={{ fontSize: 60 }}>🚀</Text>
        <Text style={s.doneTitle}>You're all set!</Text>
        <Text style={s.doneSub}>Resume uploaded. Job discovery is running 24/7.{'\n'}Check Dashboard and Matches tabs for results.</Text>
        <TouchableOpacity style={s.signOutBtn} onPress={signOut}>
          <Text style={s.signOutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>
    )
  }

  if (step === 2) {
    return (
      <View style={[s.container, { justifyContent: 'center', alignItems: 'center', padding: 32 }]}>
        <Text style={s.stepTitle}>Step 2: Upload Your Resume</Text>
        <Text style={s.stepSub}>Upload your master resume (PDF or DOCX).{'\n'}The AI will tailor it for each job automatically.</Text>
        {error ? <Text style={s.errorText}>{error}</Text> : null}
        {success ? <Text style={s.successText}>{success}</Text> : null}
        <TouchableOpacity style={[s.primaryBtn, { width: 280 }, saving && s.btnDisabled]} onPress={pickAndUploadResume} disabled={saving}>
          <Text style={s.primaryBtnText}>{saving ? 'Uploading...' : '📄 Choose Resume File (PDF/DOCX)'}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setStep(1)} style={{ marginTop: 16 }}>
          <Text style={{ color: '#64748b', fontSize: 13 }}>← Back to profile</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <ScrollView style={s.container} contentContainerStyle={{ padding: 24, paddingBottom: 60, maxWidth: 700, alignSelf: 'center', width: '100%' }}>
      <Text style={s.stepTitle}>Step 1: Your Profile</Text>
      <Text style={s.stepSub}>Fill in your details. All fields can be updated later.</Text>

      {error ? <Text style={s.errorText}>{error}</Text> : null}

      {/* Basic Info */}
      <Text style={s.sectionTitle}>Basic Information</Text>
      {[
        { label: 'Full Name *', field: 'full_name', placeholder: 'Swapnil Kaushal' },
        { label: 'Email for Notifications', field: 'notification_email', placeholder: 'you@gmail.com' },
        { label: 'Phone', field: 'phone', placeholder: '+91-9999999999' },
        { label: 'LinkedIn URL', field: 'linkedin_url', placeholder: 'https://linkedin.com/in/...' },
        { label: 'Naukri Profile URL', field: 'naukri_url', placeholder: 'https://naukri.com/...' },
        { label: 'GitHub URL', field: 'github_url', placeholder: 'https://github.com/...' },
        { label: 'Current City', field: 'current_city', placeholder: 'Bangalore' },
        { label: 'Professional Summary', field: 'professional_summary', placeholder: 'Brief summary of your experience...' },
      ].map(({ label, field, placeholder }) => (
        <View key={field} style={s.field}>
          <Text style={s.label}>{label}</Text>
          <TextInput
            style={[s.input, field === 'professional_summary' && { height: 80, textAlignVertical: 'top' }]}
            value={(form as any)[field]}
            onChangeText={v => update(field, v)}
            placeholder={placeholder}
            placeholderTextColor="#475569"
            autoCapitalize="none"
            multiline={field === 'professional_summary'}
          />
        </View>
      ))}

      {/* Experience */}
      <Text style={s.sectionTitle}>Years of Experience</Text>
      <View style={s.row}>
        {[
          { label: 'Total', field: 'experience_years' },
          { label: 'AI/ML', field: 'ai_years' },
          { label: 'Java', field: 'java_years' },
          { label: 'Frontend', field: 'frontend_years' },
          { label: 'Cloud', field: 'cloud_years' },
        ].map(({ label, field }) => (
          <View key={field} style={s.expField}>
            <Text style={s.expLabel}>{label}</Text>
            <TextInput
              style={s.expInput}
              value={(form as any)[field]}
              onChangeText={v => update(field, v)}
              keyboardType="numeric"
            />
          </View>
        ))}
      </View>

      {/* Target Roles */}
      <Text style={s.sectionTitle}>Target Roles (tap to toggle)</Text>
      <View style={s.chips}>
        {DEFAULT_ROLES.map(role => (
          <TouchableOpacity
            key={role}
            style={[s.chip, form.selectedRoles.includes(role) && s.chipActive]}
            onPress={() => toggleItem('selectedRoles', role)}
          >
            <Text style={[s.chipText, form.selectedRoles.includes(role) && s.chipTextActive]}>{role}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Skills */}
      <Text style={s.sectionTitle}>Skills (tap to toggle)</Text>
      <View style={s.chips}>
        {DEFAULT_SKILLS.map(skill => (
          <TouchableOpacity
            key={skill}
            style={[s.chip, form.selectedSkills.includes(skill) && s.chipActive]}
            onPress={() => toggleItem('selectedSkills', skill)}
          >
            <Text style={[s.chipText, form.selectedSkills.includes(skill) && s.chipTextActive]}>{skill}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Preferences */}
      <Text style={s.sectionTitle}>Preferences</Text>
      <View style={s.switchRow}>
        <Text style={s.switchLabel}>Prefer Remote Jobs</Text>
        <Switch value={form.remote_preferred} onValueChange={v => update('remote_preferred', v)} trackColor={{ true: '#6366f1' }} />
      </View>
      <View style={s.switchRow}>
        <Text style={s.switchLabel}>Open to Relocation</Text>
        <Switch value={form.open_to_relocation} onValueChange={v => update('open_to_relocation', v)} trackColor={{ true: '#6366f1' }} />
      </View>

      <TouchableOpacity style={[s.primaryBtn, saving && s.btnDisabled]} onPress={saveProfile} disabled={saving}>
        <Text style={s.primaryBtnText}>{saving ? 'Saving...' : 'Save Profile & Continue →'}</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  stepTitle: { fontSize: 22, fontWeight: '700', color: '#f1f5f9', marginBottom: 6 },
  stepSub: { fontSize: 14, color: '#94a3b8', marginBottom: 20, lineHeight: 20 },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#6366f1', marginTop: 24, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 },
  field: { marginBottom: 14 },
  label: { fontSize: 13, color: '#94a3b8', marginBottom: 5 },
  input: { backgroundColor: '#1e293b', color: '#f1f5f9', borderRadius: 10, padding: 12, fontSize: 15, borderWidth: 1, borderColor: '#334155', outlineStyle: 'none' } as any,
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  expField: { alignItems: 'center', minWidth: 70 },
  expLabel: { fontSize: 11, color: '#64748b', marginBottom: 4 },
  expInput: { backgroundColor: '#1e293b', color: '#f1f5f9', borderRadius: 8, padding: 8, width: 60, textAlign: 'center', fontSize: 18, fontWeight: '700', borderWidth: 1, borderColor: '#334155', outlineStyle: 'none' } as any,
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20, backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#334155', cursor: 'pointer' } as any,
  chipActive: { backgroundColor: '#6366f1', borderColor: '#6366f1' },
  chipText: { color: '#94a3b8', fontSize: 13 },
  chipTextActive: { color: '#fff', fontWeight: '600' },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#1e293b' },
  switchLabel: { color: '#e2e8f0', fontSize: 15 },
  primaryBtn: { backgroundColor: '#6366f1', borderRadius: 12, padding: 16, alignItems: 'center', marginTop: 28 },
  btnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  doneTitle: { fontSize: 26, fontWeight: '800', color: '#f1f5f9', marginTop: 16, textAlign: 'center' },
  doneSub: { fontSize: 14, color: '#94a3b8', textAlign: 'center', marginTop: 12, lineHeight: 22 },
  signOutBtn: { marginTop: 32, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 10, borderWidth: 1, borderColor: '#334155' },
  signOutText: { color: '#94a3b8', textAlign: 'center', fontSize: 14 },
  errorText: { color: '#ef4444', fontSize: 13, marginBottom: 12, padding: 10, backgroundColor: '#1e293b', borderRadius: 8 },
  successText: { color: '#10b981', fontSize: 13, marginBottom: 12, padding: 10, backgroundColor: '#1e293b', borderRadius: 8 },
})
