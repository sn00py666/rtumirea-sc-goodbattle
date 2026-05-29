import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { useRegister } from '@/api'
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

export const Route = createFileRoute('/(auth)/register')({
  component: RegisterPage,
})

function RegisterPage() {
  const navigate = useNavigate()
  const register = useRegister()

  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()

    if (!email.trim() || !password.trim() || !username.trim()) return

    if (password !== confirmPassword) {
      toast.error('Пароли не совпадают')
      return
    }

    try {
      await register.mutateAsync({
        body: {
          email: email.trim(),
          password,
          username: username.trim(),
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
            <UserPlus className="size-5 text-primary" />
            Создание аккаунта
          </CardTitle>
          <CardDescription>Заполните данные для регистрации</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">Имя пользователя</Label>
              <Input
                autoComplete="username"
                id="username"
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Ваш username"
                required
                type="text"
                value={username}
              />
            </div>

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
                autoComplete="new-password"
                id="password"
                minLength={6}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Придумайте пароль"
                required
                type="password"
                value={password}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="confirmPassword">Подтверждение пароля</Label>
              <Input
                autoComplete="new-password"
                id="confirmPassword"
                minLength={6}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Повторите пароль"
                required
                type="password"
                value={confirmPassword}
              />
            </div>

            <Button
              className="mt-2 w-full"
              disabled={register.isPending}
              size="lg"
              type="submit"
            >
              {register.isPending && <Spinner />}
              Создать аккаунт
              <UserPlus />
            </Button>
          </form>

          <Typography className="mt-4 text-center" variant="muted">
            Уже есть аккаунт?{' '}
            <Link
              className="text-primary underline-offset-4 hover:underline"
              to="/login"
            >
              Войти
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </div>
  )
}
