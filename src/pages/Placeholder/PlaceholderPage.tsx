export function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="font-display text-4xl">{title}</h1>
      <p className="mt-3 max-w-xl text-pine">This section is not available yet.</p>
    </section>
  )
}
