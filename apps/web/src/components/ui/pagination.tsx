"use client";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showingFrom: number;
  showingTo: number;
  totalItems: number;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  showingFrom,
  showingTo,
  totalItems,
}: PaginationProps) {
  const getVisiblePages = () => {
    const pages: (number | "...")[] = [];
    const delta = 2;

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - delta && i <= currentPage + delta)
      ) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== "...") {
        pages.push("...");
      }
    }

    return pages;
  };

  if (totalPages <= 1) return null;

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-4 pt-4 border-t border-[#2a2a2a]">
      <p className="text-[#a1a1aa] text-sm">
        Showing {showingFrom.toLocaleString()} - {showingTo.toLocaleString()} of{" "}
        {totalItems.toLocaleString()}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="bg-[#1a1a1a] border-[#2a2a2a] text-[#fafafa] hover:bg-[#252525] disabled:opacity-50"
        >
          Previous
        </Button>
        {getVisiblePages().map((page, index) =>
          page === "..." ? (
            <span key={`ellipsis-${index}`} className="px-2 text-[#a1a1aa]">
              ...
            </span>
          ) : (
            <Button
              key={page}
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page)}
              className={`min-w-[36px] ${
                currentPage === page
                  ? "bg-[#c9a227] border-[#c9a227] text-[#0a0a0a] hover:bg-[#d4af37]"
                  : "bg-[#1a1a1a] border-[#2a2a2a] text-[#fafafa] hover:bg-[#252525]"
              }`}
            >
              {page}
            </Button>
          )
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="bg-[#1a1a1a] border-[#2a2a2a] text-[#fafafa] hover:bg-[#252525] disabled:opacity-50"
        >
          Next
        </Button>
      </div>
    </div>
  );
}

interface LoadMoreProps {
  onLoadMore: () => void;
  hasMore: boolean;
  loading?: boolean;
  currentCount: number;
  totalCount: number;
}

export function LoadMore({
  onLoadMore,
  hasMore,
  loading = false,
  currentCount,
  totalCount,
}: LoadMoreProps) {
  if (!hasMore) return null;

  return (
    <div className="flex flex-col items-center gap-2 mt-4 pt-4 border-t border-[#2a2a2a]">
      <p className="text-[#a1a1aa] text-sm">
        Showing {currentCount.toLocaleString()} of {totalCount.toLocaleString()}
      </p>
      <Button
        variant="outline"
        onClick={onLoadMore}
        disabled={loading}
        className="bg-[#1a1a1a] border-[#2a2a2a] text-[#fafafa] hover:bg-[#252525]"
      >
        {loading ? "Loading..." : "Load More"}
      </Button>
    </div>
  );
}
