// Shared constants surfaced across multiple pages — previously duplicated
// (severityOptions in /incidents and /logs, statusOptions in /incidents,
// pageSizeOptions in /matching, etc.). See audit §F "Inconsistent patterns".

export const SEVERITY_OPTIONS = [
  { label: "All", value: "" },
  { label: "CRITICAL", value: "CRITICAL" },
  { label: "ERROR", value: "ERROR" },
  { label: "WARNING", value: "WARNING" },
  { label: "INFO", value: "INFO" },
] as const;

export const INCIDENT_STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "OPEN", value: "OPEN" },
  { label: "ACKNOWLEDGED", value: "ACKNOWLEDGED" },
  { label: "RECOVERING", value: "RECOVERING" },
  { label: "RESOLVED", value: "RESOLVED" },
  { label: "CLOSED", value: "CLOSED" },
] as const;

export const MATCH_STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "LIVE", value: "LIVE" },
  { label: "FINISHED", value: "FINISHED" },
  { label: "SCHEDULED", value: "SCHEDULED" },
  { label: "DISCOVERED", value: "DISCOVERED" },
] as const;

export const QUALITY_GRADE_OPTIONS = [
  { label: "All", value: "" },
  { label: "A", value: "A" },
  { label: "B", value: "B" },
  { label: "C", value: "C" },
  { label: "D", value: "D" },
  { label: "F", value: "F" },
] as const;

export const PAGE_SIZE_OPTIONS = [
  { label: "25", value: "25" },
  { label: "50", value: "50" },
  { label: "100", value: "100" },
  { label: "200", value: "200" },
] as const;

// Object-keys typed so AG Grid column defs and selects stay strict.
export type OptionValue<T extends readonly { label: string; value: string }[]> =
  T[number]["value"];