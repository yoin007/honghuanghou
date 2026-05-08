export const getDashboardErrorType = (errorOrResponse) => {
  const status =
    errorOrResponse?.response?.status ??
    errorOrResponse?.status ??
    errorOrResponse?.code

  if (status === 403) return 'forbidden'
  if (status === 401) return 'unauthorized'
  return 'error'
}

export const applyDashboardError = (errorOrResponse, forbiddenRef, errorStateRef) => {
  const type = getDashboardErrorType(errorOrResponse)
  forbiddenRef.value = type === 'forbidden'
  errorStateRef.value = type === 'forbidden' ? null : type
}
