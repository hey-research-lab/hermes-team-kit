"""Shared TOML configuration. Relative paths resolve against the config file."""
import os
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent

def load(path=None):
    path = Path(path or os.environ.get('TEAM_CONFIG', ROOT / 'config.toml')).expanduser().resolve()
    if not path.exists():
        return {}
    with path.open('rb') as stream:
        config = tomllib.load(stream)
    for name, value in config.get('paths', {}).items():
        item = Path(value).expanduser()
        config['paths'][name] = str(item if item.is_absolute() else path.parent / item)
    if config.get('telegram', {}).get('locale', 'en') not in ('en', 'ru'):
        raise ValueError('locale must be en or ru')
    roles = {p.stem for p in (ROOT / 'profiles').glob('*.md')}
    seen = set()
    key_groups = set()
    for group in config.get('seats', {}).values():
        key = group.get('api_key_env')
        if key and key in key_groups:
            raise ValueError('profiles sharing a key must use one seat group')
        if key:
            key_groups.add(key)
        for profile in group.get('profiles', []):
            if profile not in roles:
                raise ValueError('unknown profile: ' + profile)
            if profile in seen:
                raise ValueError('profile assigned to multiple groups: ' + profile)
            seen.add(profile)
    return config
