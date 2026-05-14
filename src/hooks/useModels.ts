import { useState, useEffect } from "react";
import { loadModels } from "@/services/faceApi.service";
import { MODEL_PATH } from "@/constants/thresholds";

interface UseModelsResult {
  ready: boolean;
  error: string | null;
}

export function useModels(modelPath: string = MODEL_PATH): UseModelsResult {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadModels(modelPath)
      .then(() => setReady(true))
      .catch(() =>
        setError(
          `Failed to load face-api models from "${modelPath}". ` +
            "Download model files from https://github.com/vladmandic/face-api/tree/master/model " +
            "and place them in public/models/."
        )
      );
  }, [modelPath]);

  return { ready, error };
}
