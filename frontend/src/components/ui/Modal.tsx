import React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '../../utils/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer, className }) => {
  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto overflow-x-hidden bg-[#0B2545]/50 backdrop-blur-xs p-4 sm:p-6 animate-in fade-in duration-150">
      <div className={cn("relative w-full max-w-lg transform overflow-hidden rounded-xl bg-white text-left shadow-elevated transition-all border border-[#D9E2EC]", className)}>
        <div className="flex items-center justify-between border-b border-[#D9E2EC] px-6 py-4">
          <h3 className="text-base font-semibold text-[#172B4D] tracking-tight">{title}</h3>
          <button
            type="button"
            className="rounded-lg p-1 text-[#5B6B7F] hover:text-[#172B4D] hover:bg-[#F0F4F8] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1769D2]"
            onClick={onClose}
          >
            <span className="sr-only">Close</span>
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <div className="px-6 py-5 text-sm text-[#172B4D]">
          {children}
        </div>
        {footer && (
          <div className="bg-[#F7F9FC] px-6 py-3.5 sm:flex sm:flex-row-reverse sm:gap-2.5 border-t border-[#D9E2EC]">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};

export default Modal;
