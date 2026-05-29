import { $api, queryClient } from '../query-client'

export function tasksQueryOptions() {
  return $api.queryOptions('get', '/api/tasks', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useCreateTask() {
  return $api.useMutation('post', '/api/tasks', {
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: tasksQueryOptions().queryKey,
      })
    },
  })
}

export function useTasksQuery() {
  return $api.useQuery('get', '/api/tasks', undefined, {
    retry: false,
    throwOnError: false,
  })
}
