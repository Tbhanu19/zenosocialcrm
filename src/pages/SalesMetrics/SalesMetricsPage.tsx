import { useState } from "react"
import { ApiError } from "../../api/client.ts"
import type { SalesMetricFilters } from "../../api/query-keys.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useAssignees } from "../../hooks/useCrm.ts"
import { useDebouncedValue } from "../../hooks/useDebouncedValue.ts"
import { useCampaigns } from "../../hooks/useMarketing.ts"
import { useSalesPipelineStages, useSalesPipelines } from "../../hooks/usePipeline.ts"
import { useSalesMetrics } from "../../hooks/useSalesMetrics.ts"
import { useSession } from "../../hooks/useSession.ts"
import { roleLabel } from "../../lib/utils.ts"
import type { SalesMetrics } from "../../types/sales-metrics.ts"
import { LEAD_SOURCES } from "../../types/marketing.ts"

const EMPTY_FILTERS: SalesMetricFilters = {
  dateFrom: "",
  dateTo: "",
  pipelineId: "",
  stageId: "",
  assignedTo: "",
  source: "",
  campaignId: "",
}

export function SalesMetricsPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const [scope, setScope] = useState(companyId)
  const [draft, setDraft] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const [campaignQuery, setCampaignQuery] = useState("")
  const [campaignLabel, setCampaignLabel] = useState("")
  const switchingCompany = scope !== companyId
  if (switchingCompany) {
    setScope(companyId)
    setDraft(EMPTY_FILTERS)
    setApplied(EMPTY_FILTERS)
    setCampaignQuery("")
    setCampaignLabel("")
  }
  const campaignSearch = useDebouncedValue(campaignQuery, 400).trim()
  const metricsQuery = useSalesMetrics(companyId, switchingCompany ? EMPTY_FILTERS : applied)
  const pipelinesQuery = useSalesPipelines(companyId)
  const stagesQuery = useSalesPipelineStages(companyId, draft.pipelineId)
  const assigneesQuery = useAssignees(companyId)
  const campaignLookup = useCampaigns(
    companyId,
    {
      page: 1,
      pageSize: 8,
      search: campaignSearch,
      status: "",
      channel: "",
      campaignType: "",
      startDate: "",
      endDate: "",
    },
    campaignSearch.length > 0,
  )

  if (!companyId) {
    return (
      <EmptyState title="No company selected" message="Choose a company to view sales metrics." />
    )
  }

  return (
    <section>
      <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Sales Activity</p>
      <h1 className="mt-2 font-display text-4xl">Sales Metrics</h1>
      <p className="mt-2 max-w-3xl text-pine">
        Aggregates for {session.activeCompany?.name ?? "the selected company"}. Leave the dates
        empty to include every open opportunity. Archived leads are excluded.
      </p>
      <form
        className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3"
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
          Pipeline
          <select
            className={fieldClass}
            value={draft.pipelineId}
            onChange={(event) =>
              setDraft({ ...draft, pipelineId: event.target.value, stageId: "" })
            }
          >
            <option value="">All pipelines</option>
            {(pipelinesQuery.data?.items ?? []).map((pipeline) => (
              <option key={pipeline.id} value={pipeline.id}>
                {pipeline.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Stage
          <select
            className={fieldClass}
            value={draft.stageId}
            disabled={!draft.pipelineId}
            onChange={(event) => setDraft({ ...draft, stageId: event.target.value })}
          >
            <option value="">All stages</option>
            {(stagesQuery.data ?? []).map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Assigned to
          <select
            className={fieldClass}
            value={draft.assignedTo}
            onChange={(event) => setDraft({ ...draft, assignedTo: event.target.value })}
          >
            <option value="">Anyone</option>
            {(assigneesQuery.data?.items ?? []).map((person) => (
              <option key={person.id} value={person.id}>
                {person.first_name} {person.last_name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-semibold">
          Source
          <select
            className={fieldClass}
            value={draft.source}
            onChange={(event) => setDraft({ ...draft, source: event.target.value })}
          >
            <option value="">All sources</option>
            {LEAD_SOURCES.map((source) => (
              <option key={source} value={source}>
                {roleLabel(source)}
              </option>
            ))}
          </select>
        </label>
        <div className="text-sm font-semibold">
          Campaign
          <input
            className={fieldClass}
            value={campaignQuery}
            placeholder="Search campaigns"
            onChange={(event) => setCampaignQuery(event.target.value)}
          />
          {campaignSearch ? (
            <ul className="mt-2 rounded-md border border-line bg-paper">
              {(campaignLookup.data?.items ?? []).map((campaign) => (
                <li key={campaign.id}>
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left hover:bg-cream"
                    onClick={() => {
                      setDraft({ ...draft, campaignId: campaign.id })
                      setCampaignLabel(campaign.name)
                      setCampaignQuery("")
                    }}
                  >
                    {campaign.name}
                  </button>
                </li>
              ))}
              {campaignLookup.data?.items.length === 0 ? (
                <li className="px-3 py-2 text-pine">No matching campaigns.</li>
              ) : null}
            </ul>
          ) : null}
          {draft.campaignId ? <p className="mt-1 font-normal text-pine">{campaignLabel}</p> : null}
        </div>
        <div className="flex flex-wrap items-end gap-2 md:col-span-2 xl:col-span-3">
          <button type="submit" className="rounded-md bg-ink px-4 py-2 font-semibold text-paper">
            Apply filters
          </button>
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            onClick={() => {
              setDraft(EMPTY_FILTERS)
              setApplied(EMPTY_FILTERS)
              setCampaignQuery("")
              setCampaignLabel("")
            }}
          >
            Reset
          </button>
        </div>
      </form>
      <div className="mt-8">
        {metricsQuery.isPending ? <LoadingState label="Loading sales metrics..." /> : null}
        {metricsQuery.isError ? (
          <ErrorState
            title="Unable to load sales metrics."
            message={
              metricsQuery.error instanceof ApiError
                ? metricsQuery.error.message
                : "Unable to load sales metrics."
            }
          />
        ) : null}
        {metricsQuery.data ? <MetricsBody metrics={metricsQuery.data} /> : null}
      </div>
    </section>
  )
}

function MetricsBody({ metrics }: { metrics: SalesMetrics }) {
  const summary = metrics.summary
  if (summary.total_opportunities === 0) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="No sales data"
          message="No opportunities match these filters. Archived leads are excluded."
        />
        <SalesCycleNote metrics={metrics} />
      </div>
    )
  }
  const cards = [
    ["Total opportunities", String(summary.total_opportunities)],
    ["Pipeline value", summary.total_pipeline_value],
    ["Converted", String(summary.converted_leads)],
    ["Converted value", summary.converted_value],
    ["Lost", String(summary.lost_leads)],
    ["Lost value", summary.lost_value],
    ["Conversion rate", `${summary.conversion_rate}%`],
    ["Average opportunity value", summary.average_opportunity_value],
  ] as const
  return (
    <div className="space-y-8">
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-line bg-paper px-4 py-3">
            <dt className="text-sm font-semibold text-moss">{label}</dt>
            <dd className="mt-1 font-display text-3xl">{value}</dd>
          </div>
        ))}
      </dl>
      <BarChart
        title="Pipeline value by stage"
        caption="One bar per stage that has opportunities in this filter, including unassigned."
        rows={metrics.by_stage.map((item) => ({
          key: item.stage_id ?? "unassigned",
          label: item.stage_name ?? "Unassigned",
          amount: Number(item.pipeline_value),
          detail: `${item.lead_count} opportunities`,
        }))}
      />
      <BarChart
        title="Sales trend"
        caption={`Grouped by ${metrics.interval}. Each point is opportunities created in that period.`}
        rows={metrics.trend.map((point) => ({
          key: point.period,
          label: point.period,
          amount: point.opportunity_count,
          detail: point.pipeline_value,
        }))}
      />
      <BarChart
        title="Conversions over time"
        caption="Converted leads in the same filtered set, grouped with the trend."
        rows={metrics.trend.map((point) => ({
          key: `converted-${point.period}`,
          label: point.period,
          amount: point.converted_count,
          detail: point.converted_value,
        }))}
      />
      <BarChart
        title="Pipeline by source"
        caption="Only sources that have opportunities in this filter are listed."
        rows={metrics.by_source.map((item) => ({
          key: item.source,
          label: roleLabel(item.source),
          amount: Number(item.pipeline_value),
          detail: `${item.lead_count} opportunities`,
        }))}
      />
      <MetricTable
        title="By stage"
        caption="Stage totals come from the same aggregate as the chart."
        columns={["Stage", "Opportunities", "Pipeline value", "Converted", "Converted value"]}
        rows={metrics.by_stage.map((item) => ({
          key: item.stage_id ?? "unassigned",
          cells: [
            item.stage_name ?? "Unassigned",
            String(item.lead_count),
            item.pipeline_value,
            String(item.converted_count),
            item.converted_value,
          ],
        }))}
      />
      <MetricTable
        title="By source"
        caption="Source totals are grouped in one query."
        columns={["Source", "Opportunities", "Pipeline value", "Converted", "Converted value"]}
        rows={metrics.by_source.map((item) => ({
          key: item.source,
          cells: [
            roleLabel(item.source),
            String(item.lead_count),
            item.pipeline_value,
            String(item.converted_count),
            item.converted_value,
          ],
        }))}
      />
      <MetricTable
        title="By campaign"
        caption="Campaign names are joined in the aggregate. Unattributed opportunities stay in one row."
        columns={["Campaign", "Opportunities", "Pipeline value", "Converted", "Converted value"]}
        rows={metrics.by_campaign.map((item) => ({
          key: item.campaign_id ?? "unattributed",
          cells: [
            item.campaign_name ?? "Unattributed",
            String(item.lead_count),
            item.pipeline_value,
            String(item.converted_count),
            item.converted_value,
          ],
        }))}
      />
      <MetricTable
        title="By assigned user"
        caption="Names are limited to people already assigned on this company's opportunities."
        columns={["Assigned user", "Opportunities", "Pipeline value", "Converted", "Converted value"]}
        rows={metrics.by_assigned_user.map((item) => ({
          key: item.user_id ?? "unassigned",
          cells: [
            item.user_name ?? "Unassigned",
            String(item.opportunity_count),
            item.pipeline_value,
            String(item.converted_count),
            item.converted_value,
          ],
        }))}
      />
      <section>
        <h2 className="font-display text-2xl">Expected close value</h2>
        <p className="mt-1 text-sm text-pine">
          Stored expected close dates on open opportunities. This is not a forecast.
        </p>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-line bg-paper px-4 py-3">
            <dt className="text-sm font-semibold text-moss">Upcoming</dt>
            <dd className="mt-1 font-display text-3xl">
              {metrics.expected_close.upcoming_count} · {metrics.expected_close.upcoming_value}
            </dd>
          </div>
          <div className="rounded-lg border border-line bg-paper px-4 py-3">
            <dt className="text-sm font-semibold text-moss">Overdue</dt>
            <dd className="mt-1 font-display text-3xl">
              {metrics.expected_close.overdue_count} · {metrics.expected_close.overdue_value}
            </dd>
          </div>
        </dl>
      </section>
      <SalesCycleNote metrics={metrics} />
    </div>
  )
}

function SalesCycleNote({ metrics }: { metrics: SalesMetrics }) {
  if (metrics.sales_cycle.available) {
    return null
  }
  return (
    <section className="rounded-lg border border-line bg-paper px-4 py-3">
      <h2 className="font-display text-2xl">Sales cycle</h2>
      <p className="mt-1 text-sm text-pine">
        {metrics.sales_cycle.reason ?? "Sales cycle days are not available."}
      </p>
    </section>
  )
}

function BarChart({
  title,
  caption,
  rows,
}: {
  title: string
  caption: string
  rows: Array<{ key: string; label: string; amount: number; detail: string }>
}) {
  const max = Math.max(1, ...rows.map((row) => row.amount))
  return (
    <section>
      <h2 className="font-display text-2xl">{title}</h2>
      <p className="mt-1 text-sm text-pine">{caption}</p>
      {rows.length === 0 ? <p className="mt-3 text-sm">No buckets in this range.</p> : null}
      <div className="mt-3 space-y-3">
        {rows.map((row) => (
          <div key={row.key}>
            <div className="flex justify-between gap-3 text-sm">
              <span>{row.label}</span>
              <span>
                {row.amount} · {row.detail}
              </span>
            </div>
            <div className="mt-1 h-2 rounded bg-line">
              <div className="h-2 rounded bg-pine" style={{ width: `${(row.amount / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function MetricTable({
  title,
  caption,
  columns,
  rows,
}: {
  title: string
  caption: string
  columns: string[]
  rows: Array<{ key: string; cells: string[] }>
}) {
  return (
    <section>
      <h2 className="font-display text-2xl">{title}</h2>
      <p className="mt-1 text-sm text-pine">{caption}</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-line">
              {columns.map((column) => (
                <th key={column} className="py-2 pr-4">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-line">
                {row.cells.map((cell, index) => (
                  <td key={`${row.key}-${columns[index] ?? index}`} className="py-2 pr-4">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
