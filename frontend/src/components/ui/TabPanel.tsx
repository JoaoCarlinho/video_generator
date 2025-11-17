import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../utils/cn'

export interface TabPanelProps {
  children: React.ReactNode
  isActive: boolean
  tabId: string
  className?: string
}

export const TabPanel: React.FC<TabPanelProps> = ({
  children,
  isActive,
  tabId,
  className,
}) => {
  return (
    <AnimatePresence mode="wait">
      {isActive && (
        <motion.div
          key={tabId}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.15 }}
          className={cn('w-full', className)}
          role="tabpanel"
          aria-labelledby={`tab-${tabId}`}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
