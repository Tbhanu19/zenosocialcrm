import { useState } from "react"
import { Link } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import type { LeadMetricFilters } from "../../api/query-keys.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useLeadMetrics } from "../../hooks/useLeadMetrics.ts"
import { useLeadMetricsTypes } from "../../hooks/useLeadMetricsTypes.ts"
import { useSession } from "../../hooks/useSession.ts"
import { roleLabel } from "../../lib/utils.ts"
import type { LeadMetricsType } from "../../types/lead-metrics-type.ts"
import type { LeadMetrics } from "../../types/metrics.ts"
import { LEAD_STATUSES } from "../../types/marketing.ts"

const EMPTY_FILTERS: LeadMetricFilters = {
  dateFrom: "",
  dateTo: "",
  status: "",
}

export function LeadMetricsPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const [draft, setDraft] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const metricsQuery = useLeadMetrics(companyId, applied)
  const typesQuery = useLeadMetricsTypes(companyId)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company to view lead metrics." />
  }

  const metricTypes = (typesQuery.data ?? []).filter((item) => item.status === "active")

  return (
    <section>
      <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Marketing</p>
      <h1 className="mt-2 font-display text-4xl">Lead Metrics</h1>
      <p className="mt-2 max-w-3xl text-pine">
        Counts for {session.activeCompany?.name ?? "the selected company"}. Leave the dates empty
        to include every lead. Archived leads are included only when status is Archived.
      </p>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl">Indicators</h2>
          <p className="mt-1 text-sm text-pine">
            Active metrics types and live lead counts for this organisation.
          </p>
        </div>
        <Link to="/lead-metrics-types" className="text-sm font-semibold text-pine underline">
          Manage types
        </Link>
      </div>

      {typesQuery.isPending || metricsQuery.isPending ? (
        <div className="mt-4">
          <LoadingState label="Loading indicators" />
        </div>
      ) : null}
      {typesQuery.isError ? (
        <div className="mt-4">
          <ErrorState
            message={
              typesQuery.error instanceof ApiError
                ? typesQuery.error.message
                : "Lead metrics types could not be loaded."
            }
          />
        </div>
      ) : null}
      {metricsQuery.isError ? (
        <div className="mt-4">
          <ErrorState
            title="Unable to load metrics."
            message={
              metricsQuery.error instanceof ApiError
                ? metricsQuery.error.message
                : "Unable to load metrics."
            }
          />
        </div>
      ) : null}

      {!typesQuery.isPending && !metricsQuery.isPending && metricsQuery.data ? (
        <IndicatorCards types={metricTypes} metrics={metricsQuery.data} />
      ) : null}

      <form
        className="mt-6 grid gap-3 md:grid-cols-3"
        onSubmit={(event) => {
          event.preventDefault()
          setApplied(draft)
        }}
      >
        <label className="text-sm font-semibold">
          Date from
          <input
            type="date"
            className={fieldClass}
            value={draft.dateFrom}
            onChange={(event) => setDraft({ ...draft, dateFrom: event.target.value })}
          />
        </label>
        <label className="text-sm font-semibold">
          Date to
          <input
            type="date"
            className={fieldClass}
            value={draft.dateTo}
            onChange={(event) => setDraft({ ...draft, dateTo: event.target.value })}
          />
        </label>
        <label className="text-sm font-semibold">
          Status
          <select
            className={fieldClass}
            value={draft.status}
            onChange={(event) => setDraft({ ...draft, status: event.target.value })}
          >
            <option value="">All open statuses</option>
            {LEAD_STATUSES.map((status) => (
              <option key={status} value={status}>
                {roleLabel(status)}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap items-end gap-2 md:col-span-3">
          <button type="submit" className="rounded-md bg-ink px-4 py-2 font-semibold text-paper">
            Apply filters
          </button>
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            onClick={() => {
              setDraft(EMPTY_FILTERS)
              setApplied(EMPTY_FILTERS)
            }}
          >
            Reset
          </button>
        </div>
      </form>

      <div className="mt-8">
        {metricsQuery.data ? <MetricsBody metrics={metricsQuery.data} /> : null}
      </div>
    </section>
  )
}

function IndicatorCards({
  types,
  metrics,
}: {
  types: LeadMetricsType[]
  metrics: LeadMetrics
}) {
  const summary = metrics.summary
  const liveCards = [
    { label: "Total leads", value: summary.total_leads },
    { label: "New leads", value: summary.new_leads },
    { label: "Contacted leads", value: summary.contacted_leads },
    { label: "Qualified leads", value: summary.qualified_leads },
    { label: "Converted leads", value: summary.converted_leads },
    { label: "Lost leads", value: summary.lost_leads },
    { label: "Conversion rate", value: `${summary.conversion_rate}%` },
  ]
  const typeCards = types.map((item) => ({
    label: item.name,
    value: resolveTypeIndicatorValue(item, metrics),
    hint: item.description,
  }))

  if (typeCards.length === 0 && summary.total_leads === 0) {
    return (
      <div className="mt-4">
        <EmptyState
          title="No indicators yet."
          message="Add metrics types, or create leads to see live counts here."
        />
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-6">
      {typeCards.length > 0 ? (
        <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {typeCards.map((card) => (
            <div key={card.label} className="rounded-lg border border-line bg-paper px-4 py-3">
              <dt className="text-sm font-semibold text-moss">{card.label}</dt>
              <dd className="mt-1 font-display text-3xl">{card.value}</dd>
              {card.hint ? <p className="mt-1 text-xs text-pine">{card.hint}</p> : null}
            </div>
          ))}
        </dl>
      ) : null}
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {liveCards.map((card) => (
          <div key={card.label} className="rounded-lg border border-line bg-paper px-4 py-3">
            <dt className="text-sm font-semibold text-moss">{card.label}</dt>
            <dd className="mt-1 font-display text-3xl">{card.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function resolveTypeIndicatorValue(type: LeadMetricsType, metrics: LeadMetrics): string | number {
  const key = type.name.trim().toLowerCase()
  const summary = metrics.summary
  if (key.includes("actual") || key === "total" || key.includes("total lead")) {
    return summary.total_leads
  }
  if (key.includes("new")) {
    return summary.new_leads
  }
  if (key.includes("contacted")) {
    return summary.contacted_leads
  }
  if (key.includes("qualified") && !key.includes("unqualified")) {
    return summary.qualified_leads
  }
  if (key.includes("converted") || key.includes("conversion rate")) {
    return key.includes("rate") ? `${summary.conversion_rate}%` : summary.converted_leads
  }
  if (key.includes("lost")) {
    return summary.lost_leads
  }
  if (key.includes("target")) {
    return type.value
  }
  return type.value
}

function MetricsBody({ metrics }: { metrics: LeadMetrics }) {
  return (
    <div className="space-y-8">
      {metrics.summary.total_leads === 0 ? (
        <EmptyState
          title="No lead data for selected period."
          message="Add leads or widen the date and status filters to see charts."
        />
      ) : (
        <>
          <CountChart
            title="Lead trend"
            caption={`Grouped by ${metrics.interval}. Converted leads use the same filtered set.`}
            rows={metrics.over_time.map((point) => ({
              label: point.period,
              count: point.lead_count,
              extra: `${point.converted_count} converted`,
            }))}
          />
          <CountChart
            title="Leads by status"
            caption="Open statuses stay listed even when the count is zero."
            rows={metrics.by_status.map((item) => ({
              label: roleLabel(item.status),
              count: item.count,
            }))}
          />
          <CountChart
            title="Leads by source"
            caption="Only sources that have leads in this filter are listed."
            rows={metrics.by_source.map((item) => ({
              label: roleLabel(item.source),
              count: item.count,
            }))}
          />
          <section>
            <h2 className="font-display text-2xl">Campaign performance</h2>
            <p className="mt-1 text-sm text-pine">Lead counts and converted counts. No ranking.</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-line">
                    <th className="py-2 pr-4">Campaign</th>
                    <th className="py-2 pr-4">Leads</th>
                    <th className="py-2">Converted</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.by_campaign.map((item) => (
                    <tr key={item.campaign_id ?? "unattributed"} className="border-b border-line">
                      <td className="py-2 pr-4">{item.campaign_name ?? "Unattributed"}</td>
                      <td className="py-2 pr-4">{item.lead_count}</td>
                      <td className="py-2">{item.converted_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

function CountChart({
  title,
  caption,
  rows,
}: {
  title: string
  caption: string
  rows: Array<{ label: string; count: number; extra?: string }>
}) {
  const max = Math.max(1, ...rows.map((row) => row.count))
  return (
    <section>
      <h2 className="font-display text-2xl">{title}</h2>
      <p className="mt-1 text-sm text-pine">{caption}</p>
      {rows.length === 0 ? <p className="mt-3 text-sm">No buckets in this range.</p> : null}
      <div className="mt-3 space-y-3">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="flex justify-between gap-3 text-sm">
              <span>{row.label}</span>
              <span>
                {row.count}
                {row.extra ? ` · ${row.extra}` : ""}
              </span>
            </div>
            <div className="mt-1 h-2 rounded bg-line">
              <div
                className="h-2 rounded bg-pine"
                style={{ width: `${(row.count / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <table className="mt-3 w-full text-left text-sm">
        <caption className="sr-only">{title} values</caption>
        <thead>
          <tr>
            <th className="py-1 pr-4">Label</th>
            <th className="py-1">Count</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.label}-table`}>
              <td className="py-1 pr-4">{row.label}</td>
              <td className="py-1">{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
