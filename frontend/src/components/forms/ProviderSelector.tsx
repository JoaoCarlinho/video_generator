/**
 * ProviderSelector Component
 * Allows users to choose between Replicate (cloud) and ECS (self-hosted) video generation providers
 *
 * Story 5.1: Create Provider Selector Component
 */

import React from 'react';
import { Card } from '../ui/Card';
import { RadioGroup, RadioGroupItem } from '../ui/RadioGroup';
import { Label } from '../ui/Label';
import { Badge } from '../ui/Badge';
import { Cloud, Server, Check, AlertCircle } from 'lucide-react';

export interface ProviderSelectorProps {
  /** Currently selected provider */
  value: string;

  /** Callback when provider selection changes */
  onChange: (provider: string) => void;

  /** Whether ECS provider is currently healthy and available */
  ecsAvailable: boolean;

  /** Optional className for styling */
  className?: string;
}

interface ProviderOption {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  cost: string;
  savings?: string;
  description: string;
}

const PROVIDERS: ProviderOption[] = [
  {
    id: 'replicate',
    name: 'Replicate Cloud',
    icon: Cloud,
    cost: '~$0.80/video',
    description: 'Managed cloud service with automatic scaling',
  },
  {
    id: 'ecs',
    name: 'Self-Hosted GPU',
    icon: Server,
    cost: '~$0.20/video',
    savings: '75% savings',
    description: 'Dedicated GPU cluster with lower per-video cost',
  },
];

export function ProviderSelector({
  value,
  onChange,
  ecsAvailable,
  className = '',
}: ProviderSelectorProps) {
  const handleProviderChange = (newValue: string) => {
    // Only allow selection if provider is available
    if (newValue === 'ecs' && !ecsAvailable) {
      return;
    }
    onChange(newValue);
  };

  return (
    <div className={className}>
      <Label className="text-base font-semibold mb-3 block">
        Video Generation Provider
      </Label>

      <RadioGroup
        value={value}
        onValueChange={handleProviderChange}
        className="grid grid-cols-1 md:grid-cols-2 gap-4"
      >
        {PROVIDERS.map((provider) => {
          const isSelected = value === provider.id;
          const isDisabled = provider.id === 'ecs' && !ecsAvailable;
          const Icon = provider.icon;

          return (
            <div key={provider.id} className="relative">
              <RadioGroupItem
                value={provider.id}
                id={provider.id}
                disabled={isDisabled}
                className="peer sr-only"
                aria-label={`Select ${provider.name}`}
              />

              <Label
                htmlFor={provider.id}
                className={`
                  flex flex-col cursor-pointer
                  ${isDisabled ? 'cursor-not-allowed opacity-60' : ''}
                `}
              >
                <Card
                  className={`
                    relative p-4 transition-all duration-200
                    hover:shadow-md
                    peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2
                    ${isSelected ? 'border-blue-500 border-2 shadow-sm' : 'border-gray-200'}
                    ${isDisabled ? 'bg-gray-50' : ''}
                  `}
                >
                  {/* Selected indicator */}
                  {isSelected && !isDisabled && (
                    <div className="absolute top-3 right-3">
                      <Check className="w-5 h-5 text-blue-500" />
                    </div>
                  )}

                  {/* Unavailable badge */}
                  {isDisabled && (
                    <div className="absolute top-3 right-3">
                      <Badge variant="secondary" className="bg-gray-200">
                        <AlertCircle className="w-3 h-3 mr-1" />
                        Unavailable
                      </Badge>
                    </div>
                  )}

                  {/* Provider icon */}
                  <div className="flex items-start gap-3 mb-3">
                    <div
                      className={`
                        p-2 rounded-lg
                        ${isSelected && !isDisabled ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'}
                      `}
                    >
                      <Icon className="w-6 h-6" />
                    </div>

                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 mb-1">
                        {provider.name}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {provider.description}
                      </p>
                    </div>
                  </div>

                  {/* Cost information */}
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold text-gray-900">
                        {provider.cost}
                      </span>
                      {provider.savings && (
                        <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">
                          {provider.savings}
                        </Badge>
                      )}
                    </div>
                  </div>
                </Card>
              </Label>
            </div>
          );
        })}
      </RadioGroup>

      {/* Helper text */}
      <p className="mt-3 text-sm text-gray-500">
        {ecsAvailable ? (
          <span>Both providers are currently available. Choose based on your budget and requirements.</span>
        ) : (
          <span>Self-hosted GPU cluster is currently offline. Replicate Cloud will be used automatically.</span>
        )}
      </p>
    </div>
  );
}
