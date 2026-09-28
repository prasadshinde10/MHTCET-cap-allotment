import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  pageSizeOptions?: number[];
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50, 100],
}: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize) || 1;
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between border-t border-[#D9E2EC] bg-white px-4 py-3 sm:px-6">
      <div className="flex flex-1 justify-between sm:hidden">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Next
        </Button>
      </div>
      
      <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <p className="text-xs text-[#5B6B7F]">
            Showing <span className="font-semibold text-[#172B4D]">{total === 0 ? 0 : startItem}</span> to{' '}
            <span className="font-semibold text-[#172B4D]">{endItem}</span> of{' '}
            <span className="font-semibold text-[#172B4D]">{total.toLocaleString()}</span> results
          </p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#5B6B7F]">Rows per page:</span>
            <select
              className="h-7 rounded-md border border-[#D9E2EC] bg-white px-2 text-xs text-[#172B4D] shadow-subtle focus:border-[#1769D2] focus:outline-none focus:ring-1 focus:ring-[#1769D2]"
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div>
          <nav className="isolate inline-flex -space-x-px rounded-lg shadow-subtle" aria-label="Pagination">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="relative inline-flex items-center rounded-l-lg px-2.5 py-1.5 text-[#5B6B7F] ring-1 ring-inset ring-[#D9E2EC] hover:bg-[#F0F4F8] hover:text-[#172B4D] focus:z-20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <span className="sr-only">Previous</span>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <span className="relative inline-flex items-center px-3.5 py-1.5 text-xs font-semibold text-[#172B4D] ring-1 ring-inset ring-[#D9E2EC] bg-[#F7F9FC]">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="relative inline-flex items-center rounded-r-lg px-2.5 py-1.5 text-[#5B6B7F] ring-1 ring-inset ring-[#D9E2EC] hover:bg-[#F0F4F8] hover:text-[#172B4D] focus:z-20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <span className="sr-only">Next</span>
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
}

export default Pagination;
