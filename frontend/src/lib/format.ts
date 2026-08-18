export function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function readableLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function countRecentActivity(
  earnedAtValues: string[],
  days: number,
  asOf: string = new Date().toISOString(),
) {
  const end = new Date(asOf).getTime();
  const start = end - days * 24 * 60 * 60 * 1000;
  return earnedAtValues.filter((value) => {
    const timestamp = new Date(value).getTime();
    return timestamp >= start && timestamp <= end;
  }).length;
}
