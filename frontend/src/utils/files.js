// Mirrors the backend rules in backend/app/config.py
const MB = 1024 * 1024;

export const SOURCES = {
  recording: {
    label: "Recording",
    hint: "Audio or video of the meeting",
    accept: ".mp3,.wav,.m4a,.ogg,.flac,.mp4,.mov,.mkv,.webm",
    types: {
      audio: { extensions: [".mp3", ".wav", ".m4a", ".ogg", ".flac"], maxBytes: 200 * MB },
      video: { extensions: [".mp4", ".mov", ".mkv", ".webm"], maxBytes: 1024 * MB },
    },
  },
  slides: {
    label: "Slides",
    hint: "The deck that was presented",
    accept: ".pptx,.pdf",
    types: {
      presentation: { extensions: [".pptx", ".pdf"], maxBytes: 100 * MB },
    },
  },
};

export function extensionOf(name) {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i).toLowerCase();
}

/** Returns an error sentence, or null if the file is acceptable for this source. */
export function validateFile(file, sourceKey) {
  const source = SOURCES[sourceKey];
  const ext = extensionOf(file.name);
  const match = Object.entries(source.types).find(([, t]) => t.extensions.includes(ext));
  if (!match) {
    if (ext === ".ppt") return "Old .ppt files aren't supported. Save the deck as .pptx and try again.";
    return `${file.name} isn't a supported ${source.label.toLowerCase()} file. Use ${source.accept.split(",").join(", ")}.`;
  }
  const [typeName, rule] = match;
  if (file.size === 0) return `${file.name} is empty.`;
  if (file.size > rule.maxBytes) {
    return `${file.name} is larger than the ${rule.maxBytes / MB} MB limit for ${typeName} files.`;
  }
  return null;
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < MB) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * MB) return `${(bytes / MB).toFixed(1)} MB`;
  return `${(bytes / (1024 * MB)).toFixed(2)} GB`;
}

export function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
