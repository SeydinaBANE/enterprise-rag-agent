'use client'
import { ApiKeyGuard } from '@/components/shared/ApiKeyGuard'
import { DocumentTable } from '@/components/documents/DocumentTable'
import { FileUpload } from '@/components/documents/FileUpload'
import { UrlIngest } from '@/components/documents/UrlIngest'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function DocumentsPage() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 overflow-y-auto px-4 py-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">Knowledge Base</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Gérez les documents disponibles pour {"l'"}agent RAG.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Uploader un fichier</CardTitle>
            <CardDescription>PDF, TXT, Markdown, RST — max 50 MB</CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ingérer une URL</CardTitle>
            <CardDescription>Page web accessible publiquement</CardDescription>
          </CardHeader>
          <CardContent>
            <UrlIngest />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Documents ingérés</CardTitle>
          <CardDescription>Tous les documents disponibles dans la knowledge base</CardDescription>
        </CardHeader>
        <CardContent>
          <DocumentTable />
        </CardContent>
      </Card>
    </div>
  )
}

export default function DocumentsRoute() {
  return (
    <ApiKeyGuard>
      <DocumentsPage />
    </ApiKeyGuard>
  )
}
