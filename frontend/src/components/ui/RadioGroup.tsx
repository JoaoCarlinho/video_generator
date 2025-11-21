import React from 'react';

interface RadioGroupContextType {
  value: string;
  onValueChange: (value: string) => void;
}

const RadioGroupContext = React.createContext<RadioGroupContextType | undefined>(undefined);

interface RadioGroupProps {
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
  children: React.ReactNode;
}

export function RadioGroup({ value, onValueChange, className = '', children }: RadioGroupProps) {
  return (
    <RadioGroupContext.Provider value={{ value, onValueChange }}>
      <div className={className}>{children}</div>
    </RadioGroupContext.Provider>
  );
}

interface RadioGroupItemProps {
  value: string;
  id: string;
  disabled?: boolean;
  className?: string;
  'aria-label'?: string;
}

export function RadioGroupItem({ value, id, disabled = false, className = '', ...props }: RadioGroupItemProps) {
  const context = React.useContext(RadioGroupContext);

  if (!context) {
    throw new Error('RadioGroupItem must be used within a RadioGroup');
  }

  const { value: selectedValue, onValueChange } = context;

  return (
    <input
      type="radio"
      id={id}
      value={value}
      checked={selectedValue === value}
      onChange={(e) => !disabled && onValueChange(e.target.value)}
      disabled={disabled}
      className={className}
      {...props}
    />
  );
}
