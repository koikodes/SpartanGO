// Mirrors backend/app/models.py. Keep the two in sync.
export type Role = 'student' | 'driver' | 'admin';

export interface Stop { id: string; name: string; lat: number; lng: number }

export interface Route { id: string; name: string; color: string; is_loop: boolean; stops: Stop[] }

export interface Vehicle {
  id: string;
  route_id: string;
  lat: number;
  lng: number;
  heading?: number | null;
  speed_mps?: number | null;
  passenger_load?: number | null;
  updated_at: string;
}

export interface Arrival { stop_id: string; route_id: string; vehicle_id: string; eta_seconds: number }

export interface User { id: number; email: string; name: string; role: Role }

export type RideStatus = 'pending' | 'accepted' | 'picked_up' | 'completed' | 'cancelled';

export interface Ride {
  id: number;
  user_id: number;
  route_id: string;
  pickup_stop_id: string;
  dropoff_stop_id: string;
  status: RideStatus;
  note: string | null;
  created_at: string;
}

export interface Pass { token: string; expires_in: number }

export interface PassCheck { valid: boolean; name?: string | null; reason?: string | null }
