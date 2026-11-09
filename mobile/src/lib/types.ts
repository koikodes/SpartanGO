// Mirrors backend/app/models.py. Keep the two in sync.
export type Role = 'student' | 'driver' | 'admin';

export interface TemporaryStop { name: string; lat: number; lng: number; alert_id: number; until?: string | null }

export interface Stop { id: string; name: string; lat: number; lng: number; temporary?: TemporaryStop | null }

export interface Route {
  id: string;
  name: string;
  color: string;
  is_loop: boolean;
  stops: Stop[];
  /** Title of the 'no service' alert covering this route right now, if any. */
  service_paused?: string | null;
}

export interface Vehicle {
  id: string;
  route_id: string;
  lat: number;
  lng: number;
  heading?: number | null;
  speed_mps?: number | null;
  passenger_load?: number | null;
  updated_at: string;
  source?: 'live' | 'simulated';
}

export type ArrivalKind = 'live' | 'simulated' | 'scheduled';

export interface Arrival { stop_id: string; route_id: string; vehicle_id: string | null; eta_seconds: number; kind: ArrivalKind }

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
  /** The shuttle the system assigned. Riders never choose a driver. */
  vehicle_id?: string | null;
  pickup_eta_seconds?: number | null;
  vehicle?: Vehicle | null;
}

export interface Pass { token: string; expires_in: number }

export interface PassCheck { valid: boolean; name?: string | null; reason?: string | null }

export type AlertType = 'stop_moved' | 'no_service' | 'delay' | 'announcement';

export interface ServiceAlert {
  id: number;
  type: AlertType;
  title: string;
  message: string;
  route_ids: string[];
  stop_id: string | null;
  moved_to_name: string | null;
  moved_to_lat: number | null;
  moved_to_lng: number | null;
  starts_at: string;
  ends_at: string | null;
  created_at: string;
  active: boolean;
}

export interface AlertInput {
  type: AlertType;
  title: string;
  message: string;
  route_ids: string[];
  stop_id?: string | null;
  moved_to_name?: string | null;
  moved_to_lat?: number | null;
  moved_to_lng?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  notify?: boolean;
}

export interface TrackerFix { vehicle_id: string; route_id: string; lat: number; lng: number; speed_mps?: number | null; heading?: number | null }
