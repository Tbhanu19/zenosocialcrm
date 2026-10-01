export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-paper px-4 py-8">
      <h2 className="font-display text-xl">{title}</h2>
      <p className="mt-2 max-w-xl text-pine">{message}</p>
    </div>
  )
}
