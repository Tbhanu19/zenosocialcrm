export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-40 items-center gap-3 text-moss" role="status">
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-copper" />
      <span>{label}</span>
    </div>
  )
}
