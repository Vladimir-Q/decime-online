const STORAGE_KEY = "decime.preferredMicDeviceId";

export interface AudioInputDevice {
  deviceId: string;
  label: string;
}

export function getStoredMicDeviceId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeMicDeviceId(deviceId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, deviceId);
  } catch {
    // Ignore quota / private mode errors.
  }
}

function labelForDevice(device: MediaDeviceInfo, index: number): string {
  const trimmed = device.label?.trim();
  if (trimmed) {
    return trimmed;
  }
  return `Microphone ${index + 1}`;
}

export async function listAudioInputDevices(): Promise<AudioInputDevice[]> {
  if (!navigator.mediaDevices?.enumerateDevices) {
    return [];
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((device) => device.kind === "audioinput")
    .map((device, index) => ({
      deviceId: device.deviceId,
      label: labelForDevice(device, index),
    }));
}

export async function requestMicPermission(): Promise<void> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone is not available in this browser.");
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach((track) => track.stop());
}

export function buildMicConstraints(deviceId: string | null): MediaStreamConstraints {
  if (!deviceId) {
    return { audio: true };
  }
  return {
    audio: {
      deviceId: { exact: deviceId },
    },
  };
}
