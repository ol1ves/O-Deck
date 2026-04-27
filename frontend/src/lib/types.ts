export interface WeatherData {
  tempF: number;
  feelsLikeF: number;
  highF: number;
  lowF: number;
  cond: string;
  code: number;
  hourly: Array<{ h: string; t: number }>;
  alerts: Array<{ type: string; label: string }>;
}

export interface TrainArrival {
  line: string;
  mins: number;
  dest: string;
  status: string;
  delay: number;
}

export interface Station {
  name: string;
  stop_id: string;
  lines: string[];
  primary: boolean;
  trains: TrainArrival[];
}

export interface TransitData {
  stations: Station[];
  secondary: Station[];
  alerts: string[];
}

export interface SpotifyData {
  is_playing: boolean;
  track: string | null;
  artist: string | null;
  album: string | null;
  progress: number;
  elapsed: string;
  total: string;
  art_url: string | null;
}

export interface CalendarEvent {
  id: string;
  title: string;
  time: string;
  duration: string;
  location: string;
  color: string;
  notion: { page_id: string; status: string; project: string } | null;
}

export interface CalendarData {
  events: CalendarEvent[];
  next_in: string | null;
}

export interface GitHubData {
  commits: Array<{ sha: string; msg: string; repo: string; time: string }>;
  prs: Array<{ number: number; title: string; repo: string; status: string; age: string }>;
  issues: Array<{ number: number; title: string; repo: string; label: string; age: string }>;
}

export interface RSSItem {
  id: string;
  src: string;
  title: string;
  link: string;
  summary: string;
  age: string;
}

export interface RSSData {
  items: RSSItem[];
  headlines: Array<{ src: string; title: string; age: string }>;
  ticker: string[];
}

export interface PhotosData {
  source: string;
  url: string | null;
  index: number;
  total: number;
  rotation_seconds: number;
}

export interface PomodoroData {
  running: boolean;
  phase: 'idle' | 'work' | 'break' | 'long_break';
  remaining_seconds: number;
  cycle: number;
  cycles_total: number;
  work_min: number;
  break_min: number;
  preset_name: string;
}

export type MotionMode = 'calm' | 'music' | 'rain' | 'thunder';

export interface DeviceInfo {
  callsign: string;
  name: string;
  hostname: string;
  lan_ip: string;
  uptime_seconds: number;
}

export interface IntegrationStatus {
  name: string;
  error_count: number;
  last_success: number | null;
  last_error: string | null;
}

export interface AppState {
  weather: WeatherData | null;
  transit: TransitData | null;
  spotify: SpotifyData | null;
  calendar: CalendarData | null;
  github: GitHubData | null;
  rss: RSSData | null;
  photos: PhotosData | null;
  pomodoro: PomodoroData | null;
  device: DeviceInfo | null;
  integrationStatus: IntegrationStatus[];
  uptimeOriginSeconds: number;
  uptimePolledAt: number;
  themeOverride: MotionMode | null;
  weatherWindow: '24h' | '6h';
  connected: boolean;
  motionMode: MotionMode;
}
