export interface AiPowerStatus {
  stt_enabled: boolean;
  tts_enabled: boolean;
  stt_status: string;
  tts_status: string;
  stt_warm: boolean;
  tts_containers: Record<string, string>;
  tts_containers_running: boolean;
  docker_control_enabled: boolean;
  docker_control_available: boolean;
  edge_speech?: boolean;
  orpheus_tts_base_url?: string | null;
  openai_stt_base_url?: string | null;
  stt_provider: string;
  tts_provider: string;
  last_error: string | null;
}
