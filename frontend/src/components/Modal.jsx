import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

export default function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  type = 'default', // 'default', 'confirm', 'prompt', 'alert'
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  inputValue,
  setInputValue,
  inputPlaceholder = 'Type here...',
  isDestructive = false
}) {
  // Prevent scrolling on body when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-card border border-border w-full max-w-md rounded-2xl shadow-2xl overflow-hidden"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-semibold text-foreground tracking-tight">{title}</h3>
                  {type !== 'alert' && (
                    <button
                      onClick={onClose}
                      className="text-muted hover:text-foreground transition-colors bg-card-hover hover:bg-white/[0.05] p-1.5 rounded-lg"
                    >
                      <X size={18} />
                    </button>
                  )}
                </div>
                
                {description && (
                  <p className="text-muted text-sm leading-relaxed mb-6">
                    {description}
                  </p>
                )}

                {type === 'prompt' && (
                  <div className="mb-6">
                    <input
                      type="text"
                      autoFocus
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder={inputPlaceholder}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onConfirm();
                      }}
                      className="w-full bg-background border border-border rounded-xl px-4 py-3 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 transition-all placeholder-gray-600"
                    />
                  </div>
                )}

                {children && <div className="mb-6">{children}</div>}

                <div className="flex items-center justify-end gap-3 mt-8">
                  {type !== 'alert' && (
                    <button
                      onClick={onClose}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-foreground-muted hover:text-foreground bg-card-hover hover:bg-white/[0.08] transition-colors"
                    >
                      {cancelText}
                    </button>
                  )}
                  <button
                    onClick={onConfirm}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-lg ${
                      isDestructive
                        ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20'
                        : type === 'alert'
                        ? 'bg-white text-black hover:bg-gray-200'
                        : 'bg-cyan-500 text-black hover:bg-cyan-400 shadow-cyan-500/20'
                    }`}
                  >
                    {confirmText}
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
