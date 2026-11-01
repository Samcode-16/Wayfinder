// Mirrors backend/app/schemas.py
export interface TripRequest {
  origin?: string | null;
  origin_iata?: string | null;
  destination?: string | null;
  destination_iata?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  travelers: number;
  budget?: number | null;
  currency: string;
  hotel_stars?: number | null;
  interests: string[];
  notes?: string | null;
}

export interface FlightLeg {
  airline: string;
  flight_number?: string | null;
  from_airport: string;
  to_airport: string;
  departs?: string | null;
  arrives?: string | null;
  duration_min?: number | null;
}

export interface FlightOption {
  id: string;
  airline: string;
  airline_logo?: string | null;
  price: number;
  currency: string;
  stops: number;
  total_duration_min: number;
  legs: FlightLeg[];
  link?: string | null;
  source: 'serpapi' | 'demo';
}

export interface HotelOption {
  id: string;
  name: string;
  price_per_night: number;
  currency: string;
  rating?: number | null;
  stars?: number | null;
  image?: string | null;
  link?: string | null;
  lat?: number | null;
  lon?: number | null;
  amenities: string[];
  source: 'serpapi' | 'demo';
}

export interface Activity {
  name: string;
  category: string;
  lat: number;
  lon: number;
  wikipedia?: string | null;
}

export interface DayWeather {
  date: string;
  summary: string;
  tmax?: number | null;
  tmin?: number | null;
  rain_prob?: number | null;
  precip_mm?: number | null;
  kind: 'forecast' | 'historical';
}

export interface Selection {
  flight_id: string;
  hotel_id: string;
  flights_cost: number;
  hotel_cost: number;
  daily_cost: number;
  total: number;
  budget?: number | null;
  within_budget: boolean;
  currency: string;
  notes: string[];
}

export interface ItineraryItem {
  time_of_day: 'morning' | 'afternoon' | 'evening';
  title: string;
  description: string;
  place?: string | null;
  est_cost?: number | null;
  lat?: number | null;
  lon?: number | null;
}

export interface DayPlan {
  date: string;
  theme: string;
  items: ItineraryItem[];
}

export interface TripPlan {
  title: string;
  summary: string;
  days: DayPlan[];
  tips: string[];
  local_currency?: string | null;
  exchange_rate?: number | null;
}

export type Interrupt =
  | { type: 'clarify'; missing: string[]; questions: string[]; request: TripRequest }
  | { type: 'approval'; plan: TripPlan; selection: Selection | null }
  | { type: 'ask_email'; message: string }
  | { type: 'email_confirmation'; message: string; email: string };

export interface TripData {
  request?: TripRequest;
  geo?: { lat: number; lon: number; name: string } | null;
  fx?: number;
  flights: FlightOption[];
  hotels: HotelOption[];
  activities: Activity[];
  weather: DayWeather[];
  selection?: Selection | null;
  plan?: TripPlan | null;
  warnings: string[];
}
