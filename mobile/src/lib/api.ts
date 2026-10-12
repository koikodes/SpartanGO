import type { Arrival, Pass, PassCheck, Ride, RideStatus, Role, Route, User, Vehicle } from './types';

// Set EXPO_PUBLIC_API_URL in mobile/.env. On a physical phone use your computer's LAN IP
// (e.g. http://192.168.1.20:8000), not localhost.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...headers, ...(init.headers as object) } });
  } catch {
    throw new ApiError(0, "Can't reach SpartanGO. Check your connection.");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join('\n');
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) });

export const api = {
  routes: () => request<Route[]>('/routes'),
  vehicles: (routeId?: string) => request<Vehicle[]>(`/vehicles${routeId ? `?route_id=${encodeURIComponent(routeId)}` : ''}`),
  arrivals: (routeId: string, stopId: string) =>
    request<Arrival[]>(`/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/arrivals`),

  signup: (b: { email: string; password: string; name: string; student_id: string; accepted_terms_version: string }) =>
    post<{ access_token: string; role: Role }>('/auth/signup', b),
  login: (b: { email: string; password: string }) => post<{ access_token: string; role: Role }>('/auth/login', b),
  me: () => request<User>('/me'),

  requestRide: (b: { route_id: string; pickup_stop_id: string; dropoff_stop_id: string; note?: string }) => post<Ride>('/rides', b),
  myRides: () => request<Ride[]>('/rides/mine'),
  rideQueue: () => request<Ride[]>('/rides/queue'),
  updateRide: (id: number, status: RideStatus) =>
    request<Ride>(`/rides/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  pass: () => request<Pass>('/pass'),
  verifyPass: (token: string, vehicle_id?: string) => post<PassCheck>('/pass/verify', { token, vehicle_id }),
};
