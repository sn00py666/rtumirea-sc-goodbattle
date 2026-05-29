import type { VariantProps } from 'class-variance-authority'

import { cva } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/lib/utils'

const typographyVariants = cva('', {
  defaultVariants: {
    variant: 'body',
  },
  variants: {
    variant: {
      body: 'text-base',
      h1: 'text-2xl font-bold tracking-tight',
      h2: 'text-xl font-bold',
      h3: 'text-lg font-semibold',
      large: 'text-lg',
      muted: 'text-sm text-muted-foreground',
      small: 'text-sm',
    },
  },
})

const defaultElementMap = {
  body: 'p',
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  large: 'p',
  muted: 'p',
  small: 'p',
} as const

type TypographyProps<T extends React.ElementType = 'p'> = Omit<
  React.ComponentPropsWithoutRef<T>,
  'as' | 'variant'
> & {
  as?: T
  variant?: Variant
}

type Variant = NonNullable<VariantProps<typeof typographyVariants>['variant']>

function Typography<T extends React.ElementType = 'p'>({
  as,
  className,
  variant = 'body',
  ...props
}: TypographyProps<T>) {
  const Component = as ?? defaultElementMap[variant]

  return (
    <Component
      className={cn(typographyVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Typography, typographyVariants }
