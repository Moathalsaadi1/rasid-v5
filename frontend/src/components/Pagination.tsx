import { g } from "../utils/styles";

interface Props {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}

export default function Pagination({ page, totalPages, onPage }: Props) {
  if (totalPages <= 1) return null;
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: 8,
        padding: "0 20px 20px",
      }}
    >
      <button
        onClick={() => onPage(Math.max(1, page - 1))}
        disabled={page === 1}
        style={g.btnSm}
      >
        ‹ Prev
      </button>
      <span style={{ color: "#64748b", fontSize: 13, lineHeight: "32px" }}>
        Page {page} / {totalPages}
      </span>
      <button
        onClick={() => onPage(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
        style={g.btnSm}
      >
        Next ›
      </button>
    </div>
  );
}
