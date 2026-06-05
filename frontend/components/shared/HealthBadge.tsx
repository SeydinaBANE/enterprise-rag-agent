'use client'
import { useHealth } from '@/hooks/useHealth'
import { Badge } from '@/components/ui/badge'

export function HealthBadge() {
  const { data, isLoading, isError } = useHealth()

  if (isLoading) return <Badge>Vérification…</Badge>
  if (isError || !data) return <Badge variant="red">API hors ligne</Badge>

  const allOk = data.chromadb === 'ok' && data.llm === 'ok' && data.sessions === 'ok'

  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant={allOk ? 'green' : 'yellow'}>
        {allOk ? 'Tous les services OK' : 'Service dégradé'}
      </Badge>
      <Badge variant={data.chromadb === 'ok' ? 'green' : 'red'}>
        ChromaDB {data.chromadb}
      </Badge>
      <Badge variant={data.llm === 'ok' ? 'green' : 'red'}>
        LLM {data.llm}
      </Badge>
      <Badge variant={data.sessions === 'ok' ? 'green' : 'red'}>
        Sessions {data.sessions}
      </Badge>
    </div>
  )
}
