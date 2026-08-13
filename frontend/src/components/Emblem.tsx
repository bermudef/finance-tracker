export default function Emblem({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={className}
      fill="none"
    >
      <defs>
        <linearGradient id="emblem-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" fill="url(#emblem-grad)" />
      <path
        d="M9 19.5 13.5 15l3.5 3 6-6.5"
        stroke="#fff"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="25" cy="7" r="4" fill="#f59e0b" stroke="#fff" strokeWidth="1.5" />
    </svg>
  );
}