export type ServiceHealth = {
  status: string;
  message?: string;
  engine?: string;
  supported_media?: string[];
  raw?: Record<string, unknown>;
};

export type SystemHealthResponse = {
  status: string;
  services: {
    backend_api: ServiceHealth;
    database: ServiceHealth;
    redis: ServiceHealth;
    minio: ServiceHealth;
    ai_service: ServiceHealth;
  };
};