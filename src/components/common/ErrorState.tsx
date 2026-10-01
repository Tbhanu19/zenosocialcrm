export function ErrorState({
  title = "Something went wrong",
  message,
}: {
  title?: string
  message: string
}) {
  return (
    <div className="rounded-lg border border-danger/30 bg-paper px-4 py-5" role="alert">
      <h2 className="font-display text-xl text-danger">{title}</h2>
      <p className="mt-2 text-ink">{message}</p>
    </div>
  )
}
