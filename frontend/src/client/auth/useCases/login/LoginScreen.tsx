import { CircleAlert } from 'lucide-react'
import wordmark from '@/client/shared/assets/wordmark.jpg'
import { Button } from '@/client/shared/components/ui/button'
import { Input } from '@/client/shared/components/ui/input'
import { Label } from '@/client/shared/components/ui/label'
import { copy } from '@/client/shared/lib/copy'
import { ERROR_ID, useLoginScreen, type LoginScreenProps } from './useLoginScreen'

export function LoginScreen(props: LoginScreenProps) {
  const {
    email,
    password,
    onEmailChange,
    onPasswordChange,
    emailRef,
    passwordRef,
    fieldProps,
    expected,
    submit,
    ...status
  } = useLoginScreen(props)
  const submitting = status.state === 'submitting'

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
              onChange={(e) => onEmailChange(e.target.value)}
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
              onChange={(e) => onPasswordChange(e.target.value)}
              {...fieldProps('password')}
            />
          </div>
          <p id={ERROR_ID} role="alert" className="flex gap-2 text-destructive empty:hidden">
            {status.state === 'error' && (
              <>
                <CircleAlert size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden className="mt-0.5" />
                {status.message}
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
