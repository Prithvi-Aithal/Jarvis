import { useState, useEffect, useCallback } from 'react'
import { fetchStress } from '../api'

export interface JarvisData {
  stress_level: string
  message: string
  therapy: string
  spotify: string
  features: {
    screen_time: number
    continuous_usage: number
    night_usage: number
    app_switches: number
    breaks: number
    productive_ratio: number
  }
}

const REFRESH_INTERVAL = 30_000 // 30 seconds

// FIX: Expose a manual refetch function so components can trigger a refresh
// (e.g. a "Refresh now" button) without waiting for the 30s poll.
export function useJarvisData() {
  const [data, setData] = useState<JarvisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchData = useCallback(() => {
    fetchStress()
      .then(d => { setData(d); setError(null); setLastUpdated(new Date()) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  // Manual refresh: show the loading state, then fetch
  const refetch = useCallback(() => {
    setLoading(true)
    fetchData()
  }, [fetchData])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchData])

  // FIX: Return refetch so callers can trigger manual refresh
  return { data, loading, error, lastUpdated, refetch }
}
