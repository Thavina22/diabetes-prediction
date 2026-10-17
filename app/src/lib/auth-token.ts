'use client';

import { createContext, useContext } from 'react';

export type TokenGetter = () => Promise<string | null>;

const noopToken: TokenGetter = async () => null;

export const TokenContext = createContext<TokenGetter>(noopToken);

export function useApiToken(): TokenGetter {
  return useContext(TokenContext);
}
