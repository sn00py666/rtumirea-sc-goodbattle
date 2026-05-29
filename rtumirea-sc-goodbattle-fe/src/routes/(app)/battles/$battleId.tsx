import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/(app)/battles/$battleId')({
  beforeLoad: ({ params }) => {
    throw redirect({
      params: { battleId: params.battleId },
      to: '/battle-analytics/$battleId',
    })
  },
  component: LegacyBattleRedirect,
})

function LegacyBattleRedirect() {
  return null
}
