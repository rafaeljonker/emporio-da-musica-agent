import { CircleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { login, warmExpected } from '@/client/shared/lib/api'
import type { WarmStatus } from '@/client/shared/lib/apiTypes'
import wordmark from '@/client/shared/assets/wordmark.jpg'
import { Button } from '@/client/shared/components/ui/button'
import { Input } from '@/client/shared/components/ui/input'
import { Label } from '@/client/shared/components/ui/label'
import { copy } from '@/client/shared/lib/copy'
import { ceil10 } from '@/client/warmup/domain/format'

type LoginError = 'empty' | 'invalid' | 'network' | 'expired' | null

const ERROR_ID = 'login-erro'

export function LoginScreen({ expired, onSignedIn }: { expired?: boolean; onSignedIn: (warm: WarmStatus) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // After an expiry the line sits where login errors go; the fields are not marked.
  const [error, setError] = useState<LoginError>(expired ? 'expired' : null)
  const [invalid, setInvalid] = useState({ email: false, password: false })
  const [submitting, setSubmitting] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  // The same measured expectation the warm-up shows; none when the model is always ready.
  const [expected, setExpected] = useState(0)
  useEffect(() => {
    void warmExpected().then(
      (res) => res.ok && setExpected(res.data.mode === 'provider_api' ? 0 : ceil10(res.data.expected_seconds)),
    )
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return
    if (!email || !password) {
      setError('empty')
      setInvalid({ email: !email, password: !password })
      ;(email ? passwordRef : emailRef).current?.focus()
      return
    }
    setSubmitting(true)
    setError(null)
    const res = await login(email, password)
    if (res.ok) return onSignedIn(res.data)
    setSubmitting(false)
    if (res.error.code === 'invalid_credentials') {
      setError('invalid')
      setInvalid({ email: true, password: true })
      emailRef.current?.focus()
    } else {
      // Network, 5xx and 429: the fields are not the problem, so they are not marked.
      setError('network')
      setInvalid({ email: false, password: false })
    }
  }

  const fieldProps = (field: 'email' | 'password') => ({
    'aria-invalid': invalid[field] || undefined,
    'aria-describedby': error ? ERROR_ID : undefined,
  })

  return (
    <div className="surface-paper min-h-dvh px-4 pt-8 pb-12 md:flex md:items-center md:justify-center md:pt-12">
      <main className="mx-auto w-full max-w-md">
        <img
          src={wordmark}
          alt={copy.login.wordmarkAlt}
          className="mx-auto aspect-[16/7] w-full max-w-[18.75rem] object-cover dark:hidden"
        />
        <h1 className="font-display mt-4 text-center text-[1.75rem] leading-tight font-semibold text-balance">
          {copy.login.title}
        </h1>
        <p className="tagline mt-2 text-center">{copy.login.tagline}</p>

        <form noValidate onSubmit={submit} className="surface-wood mt-8 flex flex-col gap-4 rounded-lg bg-card p-6 md:p-8">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">{copy.login.email}</Label>
            <Input
              ref={emailRef}
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                setInvalid((v) => ({ ...v, email: false }))
              }}
              {...fieldProps('email')}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">{copy.login.password}</Label>
            <Input
              ref={passwordRef}
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                setInvalid((v) => ({ ...v, password: false }))
              }}
              {...fieldProps('password')}
            />
          </div>
          <p id={ERROR_ID} role="alert" className="flex gap-2 text-destructive empty:hidden">
            {error && (
              <>
                <CircleAlert size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="mt-0.5" />
                {copy.login[error]}
              </>
            )}
          </p>
          <Button type="submit" className="w-full" aria-busy={submitting || undefined}>
            {submitting ? copy.login.submitting : copy.login.submit}
          </Button>
          <p role="status" className="sr-only">
            {submitting ? copy.login.submitting : ''}
          </p>
        </form>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          {copy.login.demoNote}
          {expected > 0 && (
            <>
              <br />
              {copy.login.warmNote(expected)}
            </>
          )}
        </p>
      </main>
    </div>
  )
}
