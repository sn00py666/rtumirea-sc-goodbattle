import createClient from 'openapi-fetch'

import type { paths } from './__generated__/schema'

export const fetchClient = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL,
  credentials: 'include',
})
