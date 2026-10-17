'use client';

import * as React from 'react';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { cn } from '@/lib/utils';

interface NumberFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  unit?: string;
  error?: string;
}

export function NumberField({
  label,
  hint,
  unit,
  error,
  className,
  id,
  ...props
}: NumberFieldProps) {
  const fieldId = id ?? props.name;
  return (
    <div className="space-y-1.5">
      <Label htmlFor={fieldId}>
        {label}
        {unit && <span className="ml-1 text-xs text-muted-foreground">({unit})</span>}
      </Label>
      <Input
        id={fieldId}
        type="number"
        inputMode="decimal"
        className={cn(error && 'border-destructive focus-visible:ring-destructive', className)}
        aria-invalid={Boolean(error)}
        {...props}
      />
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

interface SelectFieldProps {
  label: string;
  value?: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  hint?: string;
  name?: string;
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  hint,
}: SelectFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder ?? 'Select…'} />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
