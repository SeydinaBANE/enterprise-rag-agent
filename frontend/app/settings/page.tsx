'use client'
import { useState } from 'react'
import { Eye, EyeOff, Save } from 'lucide-react'
import { toast } from 'sonner'
import { useConfigStore } from '@/lib/store/config'
import { HealthBadge } from '@/components/shared/HealthBadge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function SettingsPage() {
  const { apiKey, apiUrl, setApiKey, setApiUrl } = useConfigStore()
  const [keyDraft, setKeyDraft] = useState(apiKey)
  const [urlDraft, setUrlDraft] = useState(apiUrl)
  const [showKey, setShowKey] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setApiKey(keyDraft.trim())
    setApiUrl(urlDraft.trim() || 'http://localhost:8000')
    toast.success('Paramètres sauvegardés')
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 overflow-y-auto px-4 py-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">Paramètres</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Configuration de la connexion au backend.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Connexion API</CardTitle>
          <CardDescription>
            La clé API est stockée localement dans votre navigateur.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-neutral-700" htmlFor="api-key">
                Clé API
              </label>
              <div className="relative">
                <Input
                  id="api-key"
                  type={showKey ? 'text' : 'password'}
                  value={keyDraft}
                  onChange={(e) => setKeyDraft(e.target.value)}
                  placeholder="Valeur de API_KEY dans votre .env"
                  className="pr-10"
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                  aria-label={showKey ? 'Masquer la clé' : 'Afficher la clé'}
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-neutral-700" htmlFor="api-url">
                URL du backend
              </label>
              <Input
                id="api-url"
                type="url"
                value={urlDraft}
                onChange={(e) => setUrlDraft(e.target.value)}
                placeholder="http://localhost:8000"
              />
            </div>

            <Button type="submit" className="w-full gap-2">
              <Save className="h-4 w-4" />
              Sauvegarder
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Statut des services</CardTitle>
          <CardDescription>Mis à jour toutes les 30 secondes.</CardDescription>
        </CardHeader>
        <CardContent>
          <HealthBadge />
        </CardContent>
      </Card>
    </div>
  )
}
