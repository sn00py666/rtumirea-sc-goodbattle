import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { Crown, ExternalLink, LogIn, Users } from 'lucide-react'
import { useState, ViewTransition } from 'react'

import { useJoinRoom } from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Spinner,
  Typography,
} from '@/components/ui'
import Logo from '@/icons/logo.svg'

export const Route = createFileRoute('/(app)/')({
  component: Index,
})

function Index() {
  const navigate = useNavigate()
  const joinRoom = useJoinRoom()

  const [roomCode, setRoomCode] = useState('')

  async function handleJoinSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()

    try {
      const data = await joinRoom.mutateAsync({
        body: {
          code: roomCode.trim(),
        },
      })

      void navigate({
        params: { roomId: data.room_id },
        to: '/rooms/$roomId',
      })
    } catch {
      return
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center gap-24 px-16">
      <div className="flex flex-col items-center gap-8">
        <Logo className="size-56 drop-shadow-2xl" />
        <div className="text-center">
          <Typography className="text-5xl" variant="h1">
            Good Battle
          </Typography>
          <Typography className="mt-3 text-muted-foreground" variant="large">
            Платформа для организации и проведения соревнований
          </Typography>
        </div>
      </div>

      <div className="flex w-full max-w-md flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Crown className="size-5 text-primary" />
              Организатор
            </CardTitle>
            <CardDescription>
              Создайте свою комнату и пригласите участников
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" size="lg">
              <Link to="/create-room">
                Создать комнату
                <ExternalLink />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Users className="size-5 text-primary" />
              Участник
            </CardTitle>
            <CardDescription>
              Присоединитесь к существующей комнате
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex flex-col gap-4" onSubmit={handleJoinSubmit}>
              <ViewTransition>
                <Input
                  disabled={joinRoom.isPending}
                  onChange={(e) => setRoomCode(e.target.value)}
                  placeholder="Код комнаты"
                  required
                  type="text"
                  value={roomCode}
                />

                <Button
                  className="w-full"
                  disabled={joinRoom.isPending}
                  size="lg"
                  type="submit"
                >
                  {joinRoom.isPending && <Spinner />}
                  Войти
                  <LogIn />
                </Button>
              </ViewTransition>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
