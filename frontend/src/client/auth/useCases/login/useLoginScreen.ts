import { useRef, useState, type FormEvent, type RefObject } from 'react'
import { login } from '@/client/shared/lib/api'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import { copy } from '@/client/shared/lib/copy'
import { errorMessage } from '@/client/shared/lib/errorMessage'
import { useWarmExpected } from './useWarmExpected'

export const ERROR_ID = 'login-erro'

export interface LoginScreenProps {
  expired?: boolean
  onSignedIn: (warm: WarmStatus) => void
}

type Field = 'email' | 'password'
type Reason = 'empty' | 'invalid' | 'network' | 'expired'
type Status = { state: 'idle' } | { state: 'submitting' } | { state: 'error'; reason: Reason; message: string }

export type LoginScreenView = Status & {
  email: string
  password: string
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  emailRef: RefObject<HTMLInputElement | null>
  passwordRef: RefObject<HTMLInputElement | null>
  fieldProps: (field: Field) => { 'aria-invalid': true | undefined; 'aria-describedby': string | undefined }
  /** Seconds the warm-up is expected to take; 0 shows no note. */
  expected: number
  submit: (e: FormEvent) => Promise<void>
}

const failed = (reason: Reason, message: string): Status => ({ state: 'error', reason, message })

export function useLoginScreen({ expired, onSignedIn }: LoginScreenProps): LoginScreenView {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // After an expiry the line sits where login errors go; the fields are not marked.
  const [status, setStatus] = useState<Status>(expired ? failed('expired', copy.login.expired) : { state: 'idle' })
  const [invalid, setInvalid] = useState({ email: false, password: false })
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const warm = useWarmExpected()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (status.state === 'submitting') return
    if (!email || !password) {
      setStatus(failed('empty', copy.login.empty))
      setInvalid({ email: !email, password: !password })
      ;(email ? passwordRef : emailRef).current?.focus()
      return
    }
    setStatus({ state: 'submitting' })
    const res = await login(email, password)
    if (res.ok) return onSignedIn(res.data)
    const message = errorMessage(res.error, 'login')
    if (res.error.code === 'invalid_credentials') {
      setStatus(failed('invalid', message))
      setInvalid({ email: true, password: true })
      emailRef.current?.focus()
    } else {
      // Network, 5xx and 429: the fields are not the problem, so they are not marked.
      setStatus(failed('network', message))
      setInvalid({ email: false, password: false })
    }
  }

  return {
    ...status,
    email,
    password,
    onEmailChange: (value) => {
      setEmail(value)
      setInvalid((v) => ({ ...v, email: false }))
    },
    onPasswordChange: (value) => {
      setPassword(value)
      setInvalid((v) => ({ ...v, password: false }))
    },
    emailRef,
    passwordRef,
    fieldProps: (field) => ({
      'aria-invalid': invalid[field] || undefined,
      'aria-describedby': status.state === 'error' ? ERROR_ID : undefined,
    }),
    expected: warm.state === 'success' ? warm.seconds : 0,
    submit,
  }
}
