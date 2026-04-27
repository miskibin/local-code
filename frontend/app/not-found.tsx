import ErrorState from "./_components/ErrorState"

export default function NotFound() {
  return <ErrorState kind="404" primaryHref="/" secondaryHref="/?new=1" />
}
