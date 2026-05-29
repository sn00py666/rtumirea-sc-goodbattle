import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { LogIn, Mail } from 'lucide-react'
import { useState } from 'react'

import { useLogin } from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Spinner,
  Typography,
} from '@/components/ui'

export const Route = createFileRoute('/(auth)/login')({
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const login = useLogin()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()

    if (!email.trim() || !password.trim()) return

    try {
      await login.mutateAsync({
        body: {
          email: email.trim(),
          password,
        },
      })
      void navigate({ to: '/' })
    } catch {
      return
    }
  }

  return (
    <div className="w-full max-w-md">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <LogIn className="size-5 text-primary" />
            Вход в аккаунт
          </CardTitle>
          <CardDescription>Введите email и пароль для входа</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                autoComplete="email"
                id="email"
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                type="email"
                value={email}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Пароль</Label>
              <Input
                autoComplete="current-password"
                id="password"
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Введите пароль"
                required
                type="password"
                value={password}
              />
            </div>

            <Button
              className="mt-2 w-full"
              disabled={login.isPending}
              size="lg"
              type="submit"
            >
              {login.isPending && <Spinner />}
              Войти
              <Mail />
            </Button>
          </form>

          <Typography className="mt-4 text-center" variant="muted">
            Нет аккаунта?{' '}
            <Link
              className="text-primary underline-offset-4 hover:underline"
              to="/register"
            >
              Зарегистрироваться
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </div>
  )
}
