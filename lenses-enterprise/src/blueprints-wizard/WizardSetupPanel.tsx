import { useCallback, useEffect, useState } from 'react'
import { apiGetJson } from '../api/http'
import type { WizardSessionDocumentJson } from '../api/blueprintsWizard'
import { WorkspaceWbsPathCombo, type WbsProjectPayload } from './WorkspaceWbsPathCombo'

type Props = {
  document: WizardSessionDocumentJson
  onApply: (next: WizardSessionDocumentJson) => void
  disabled: boolean
  createRepoBusy: boolean
  createRepoError: string | null
  onCreateRepo: () => void
}

function asRecord(v: unknown): Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}

export function WizardSetupPanel({
  document,
  onApply,
  disabled,
  createRepoBusy,
  createRepoError,
  onCreateRepo,
}: Props) {
  const pl = document.payload
  const title = typeof pl.title === 'string' ? pl.title : ''
  const purpose = typeof pl.purpose === 'string' ? pl.purpose : ''
  const state = typeof pl.state === 'string' ? pl.state : 'draft'
  const mode = typeof pl.mode === 'string' ? pl.mode : 'existing_workspace'
  const scope = asRecord(pl.scope)
  const wbsRel = typeof scope.wbs_rel === 'string' ? scope.wbs_rel : ''
  const roadmapRel = typeof scope.roadmap_rel === 'string' ? scope.roadmap_rel : ''
  const sectionId = typeof scope.roadmap_section_id === 'string' ? scope.roadmap_section_id : ''
  const nd = asRecord(pl.new_product_draft)
  const repoName = typeof nd.repo_name === 'string' ? nd.repo_name : ''
  const visibility = typeof nd.visibility === 'string' ? nd.visibility : 'private'
  const accountType = typeof nd.account_type === 'string' ? nd.account_type : 'user'
  const owner = typeof nd.owner === 'string' ? nd.owner : ''
  const license = typeof nd.license === 'string' ? nd.license : ''
  const description = typeof nd.description === 'string' ? nd.description : ''
  const createdUrl =
    typeof pl.created_repo_url === 'string' && pl.created_repo_url.startsWith('http')
      ? pl.created_repo_url
      : ''

  const [wbsProjects, setWbsProjects] = useState<WbsProjectPayload[]>([])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await apiGetJson<{ projects?: WbsProjectPayload[] }>('/api/wbs-management')
        const projects = Array.isArray(data.projects) ? data.projects : []
        if (!cancelled) setWbsProjects(projects)
      } catch {
        if (!cancelled) setWbsProjects([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const patch = useCallback(
    (fn: (prev: Record<string, unknown>) => Record<string, unknown>) => {
      const nextPayload = fn({ ...document.payload })
      onApply({ ...document, payload: nextPayload })
    },
    [document, onApply],
  )

  return (
    <section className="ks-wizard-flow__panel" aria-labelledby="bpw-setup-heading">
      <h2 id="bpw-setup-heading">Session setup</h2>
      <p className="ks-wizard-flow__muted forge-support" style={{ marginTop: 0 }}>
        Scope and product metadata stay in this session until you create a remote repository (optional).
      </p>
      <div className="ks-wizard-flow__grid">
        <label className="forge-support">
          Title
          <input
            className="le-input"
            type="text"
            value={title}
            disabled={disabled}
            onChange={(e) => patch((p) => ({ ...p, title: e.target.value }))}
            style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
          />
        </label>
        <label className="forge-support">
          State
          <select
            className="le-select"
            value={state}
            disabled={disabled}
            onChange={(e) => patch((p) => ({ ...p, state: e.target.value }))}
            style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
          >
            <option value="draft">draft</option>
            <option value="ready">ready</option>
            <option value="archived">archived</option>
          </select>
        </label>
      </div>
      <label className="forge-support" style={{ display: 'block', marginTop: '0.65rem' }}>
        Purpose
        <textarea
          className="le-input"
          value={purpose}
          disabled={disabled}
          rows={2}
          onChange={(e) => patch((p) => ({ ...p, purpose: e.target.value }))}
          style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
        />
      </label>
      <fieldset className="forge-support" style={{ marginTop: '0.75rem', border: 'none', padding: 0 }}>
        <legend className="forge-support" style={{ fontWeight: 600, marginBottom: '0.35rem' }}>
          Product mode
        </legend>
        <label className="forge-support" style={{ marginRight: '1rem' }}>
          <input
            type="radio"
            name="bpw-mode"
            checked={mode === 'existing_workspace'}
            disabled={disabled}
            onChange={() => patch((p) => ({ ...p, mode: 'existing_workspace' }))}
          />{' '}
          Existing workspace scope
        </label>
        <label className="forge-support">
          <input
            type="radio"
            name="bpw-mode"
            checked={mode === 'new_product'}
            disabled={disabled}
            onChange={() => patch((p) => ({ ...p, mode: 'new_product' }))}
          />{' '}
          New product (draft repo metadata)
        </label>
      </fieldset>

      {mode === 'existing_workspace' ? (
        <div className="ks-wizard-flow__grid" style={{ marginTop: '0.75rem' }}>
          <label className="forge-support">
            WBS file (relative path)
            <WorkspaceWbsPathCombo
              id="bpw-wbs-rel"
              value={wbsRel}
              disabled={disabled}
              projects={wbsProjects}
              onChange={(next) =>
                patch((p) => ({
                  ...p,
                  scope: { ...asRecord(p.scope), wbs_rel: next || null },
                }))
              }
            />
            <span className="ks-wizard-flow__muted" style={{ display: 'block', marginTop: '0.4rem', fontSize: '0.82rem' }}>
              Open the list to reuse a path from an existing repo, or type any relative path (for example a new product
              folder you will add under the workspace).
            </span>
          </label>
          <label className="forge-support">
            Roadmap file (relative path)
            <input
              className="le-input"
              type="text"
              value={roadmapRel}
              disabled={disabled}
              placeholder="e.g. myproject/docs/ROADMAP.md"
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  scope: { ...asRecord(p.scope), roadmap_rel: e.target.value || null },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            />
          </label>
          <label className="forge-support">
            Roadmap section id (optional)
            <input
              className="le-input"
              type="text"
              value={sectionId}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  scope: { ...asRecord(p.scope), roadmap_section_id: e.target.value || null },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            />
          </label>
        </div>
      ) : (
        <div className="ks-wizard-flow__grid" style={{ marginTop: '0.75rem' }}>
          <label className="forge-support">
            Repository name
            <input
              className="le-input"
              type="text"
              value={repoName}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), repo_name: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
            />
          </label>
          <label className="forge-support">
            Visibility (intent)
            <select
              className="le-select"
              value={visibility}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), visibility: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            >
              <option value="private">private</option>
              <option value="public">public</option>
            </select>
          </label>
          <label className="forge-support">
            Account type
            <select
              className="le-select"
              value={accountType}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), account_type: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            >
              <option value="user">User</option>
              <option value="org">Organization</option>
            </select>
          </label>
          <label className="forge-support">
            Owner (GitHub user or org)
            <input
              className="le-input"
              type="text"
              value={owner}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), owner: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            />
          </label>
          <label className="forge-support">
            License (optional)
            <input
              className="le-input"
              type="text"
              value={license}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), license: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            />
          </label>
          <label className="forge-support" style={{ gridColumn: '1 / -1' }}>
            Description
            <textarea
              className="le-input"
              rows={2}
              value={description}
              disabled={disabled}
              onChange={(e) =>
                patch((p) => ({
                  ...p,
                  new_product_draft: { ...asRecord(p.new_product_draft), description: e.target.value },
                }))
              }
              style={{ display: 'block', width: '100%', marginTop: '0.25rem', boxSizing: 'border-box' }}
            />
          </label>
        </div>
      )}

      {mode === 'new_product' && (
        <div style={{ marginTop: '0.75rem' }}>
          {createdUrl ? (
            <p className="forge-support">
              Created:{' '}
              <a href={createdUrl} className="forge-support" target="_blank" rel="noreferrer">
                {createdUrl}
              </a>
            </p>
          ) : (
            <>
              <button
                type="button"
                className="le-btn le-btn--primary"
                disabled={
                  disabled ||
                  createRepoBusy ||
                  !repoName.trim() ||
                  (accountType === 'org' && !owner.trim())
                }
                onClick={onCreateRepo}
              >
                {createRepoBusy ? 'Creating…' : 'Create GitHub repository…'}
              </button>
              <p className="forge-support ks-wizard-flow__muted" style={{ marginTop: '0.35rem' }}>
                Requires <code className="le-mono">GITHUB_TOKEN</code> or{' '}
                <code className="le-mono">LENSES_GITHUB_TOKEN</code> on the Lenses server and loopback or{' '}
                <code className="le-mono">LENSES_ALLOW_ACTIONS</code>. You will confirm in a dialog.
              </p>
              {createRepoError && (
                <p className="forge-support" role="alert" style={{ marginTop: '0.35rem' }}>
                  {createRepoError}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
