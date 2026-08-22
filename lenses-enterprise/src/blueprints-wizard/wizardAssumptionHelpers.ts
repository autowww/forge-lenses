/**
 * Client-side helpers for wizard_domain assumption ledger (mirrors Python normalize rules loosely).
 * Experimental Blueprints Wizard.
 */

import { normalizeAssumptionLedger } from './wizardDomainNormalize'
import type { AssumptionLedgerEntryJson } from './wizardDomainTypes'

export function newAssumptionEntryId(): string {
  const a = new Uint8Array(10)
  crypto.getRandomValues(a)
  return Array.from(a, (b) => b.toString(16).padStart(2, '0')).join('')
}

export function appendAssumptionEntry(
  ledger: AssumptionLedgerEntryJson[],
  partial: Pick<AssumptionLedgerEntryJson, 'text'> & Partial<Omit<AssumptionLedgerEntryJson, 'text'>>,
): AssumptionLedgerEntryJson[] {
  const entry: AssumptionLedgerEntryJson = {
    id: partial.id ?? newAssumptionEntryId(),
    text: partial.text ?? '',
    source: partial.source,
    created_at: partial.created_at,
    status: partial.status,
  }
  return normalizeAssumptionLedger([...ledger, entry])
}

export function removeAssumptionById(
  ledger: AssumptionLedgerEntryJson[],
  id: string,
): AssumptionLedgerEntryJson[] {
  return ledger.filter((e) => e.id !== id)
}

export function updateAssumptionEntry(
  ledger: AssumptionLedgerEntryJson[],
  id: string,
  patch: Partial<AssumptionLedgerEntryJson>,
): AssumptionLedgerEntryJson[] {
  return normalizeAssumptionLedger(
    ledger.map((e) => (e.id === id ? { ...e, ...patch, id: e.id } : e)),
  )
}
