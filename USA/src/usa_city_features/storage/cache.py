import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Any

class LocalCache:
    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, source: str, dataset: str, version: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        key_str = f"{source}_{dataset}_{version}_{param_str}"
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

    def _get_cache_path(self, source: str, dataset: str, version: str, cache_key: str) -> Path:
        path = self.base_dir / source / dataset / version
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{cache_key}.json"

    def get(self, source: str, dataset: str, version: str, params: dict) -> Optional[Any]:
        cache_key = self._get_cache_key(source, dataset, version, params)
        cache_path = self._get_cache_path(source, dataset, version, cache_key)
        
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def set(self, source: str, dataset: str, version: str, params: dict, data: Any) -> str:
        cache_key = self._get_cache_key(source, dataset, version, params)
        cache_path = self._get_cache_path(source, dataset, version, cache_key)
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            
        return str(cache_path)
