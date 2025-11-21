import { Check } from 'lucide-react'
import { cn } from '@/utils/cn'

interface StepIndicatorProps {
  currentStep: number
  totalSteps: number
  steps: Array<{ label: string; description?: string }>
}

export const StepIndicator = ({ currentStep, totalSteps, steps }: StepIndicatorProps) => {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between relative">
        {/* Progress line */}
        <div className="absolute top-3 left-0 right-0 h-0.5 bg-olive-600/30 -z-10" />
        <div 
          className="absolute top-3 left-0 h-0.5 bg-gradient-gold transition-all duration-500 -z-10"
          style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
        />
        
        {steps.map((step, index) => {
          const stepNumber = index + 1
          const isCompleted = stepNumber < currentStep
          const isCurrent = stepNumber === currentStep
          const isUpcoming = stepNumber > currentStep
          
          return (
            <div key={stepNumber} className="flex flex-col items-center flex-1 relative">
              {/* Step circle */}
              <div
                className={cn(
                  'relative w-6 h-6 rounded-full flex items-center justify-center border-2 transition-all duration-300',
                  isCompleted && 'bg-gold border-gold shadow-gold',
                  isCurrent && 'bg-gold/20 border-gold shadow-gold scale-105',
                  isUpcoming && 'bg-olive-800/50 border-olive-600'
                )}
              >
                {isCompleted ? (
                  <Check className="w-3 h-3 text-gold-foreground" />
                ) : (
                  <span className={cn(
                    'text-xs font-bold',
                    isCurrent ? 'text-gold' : 'text-muted-gray'
                  )}>
                    {stepNumber}
                  </span>
                )}
                {isCurrent && (
                  <div className="absolute inset-0 rounded-full bg-gold/20 animate-pulse" />
                )}
              </div>
              
              {/* Step label */}
              <div className="mt-1.5 text-center">
                <p className={cn(
                  'text-xs font-semibold',
                  isCurrent ? 'text-gold' : isCompleted ? 'text-off-white' : 'text-muted-gray'
                )}>
                  {step.label}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

