import configparser
from typing import Dict, Any
import re
import shlex

class PalworldConfigManager:
    """Handles PalWorld configuration file operations"""
    
    def __init__(self):
        pass
        
    def load_palworld_config(self, config_path: str) -> Dict[str, Dict[str, str]]:
        """Load Palworld configuration file using custom parser"""
        try:
            # Try custom parser first
            return self._load_palworld_config_custom(config_path)
        except Exception as e:
            # Fallback to configparser
            print(f"Custom parser failed, falling back to configparser: {e}")
            return self._load_palworld_config_ini(config_path)
    
    def _load_palworld_config_custom(self, config_path: str) -> Dict[str, Dict[str, str]]:
        """Custom parser that handles single-line PalWorld config format, robust to comments and blank lines anywhere"""
        settings = {"PalWorldSettings": {}}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Split into lines and skip comments/blank lines
            lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith((';', '#'))]
            current_section = None
            for line in lines:
                # Section header
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1]
                    # Treat any section as PalWorldSettings for GUI compatibility
                    current_section = 'PalWorldSettings'
                    if current_section not in settings:
                        settings[current_section] = {}
                    continue
                # OptionSettings line
                if line.startswith('OptionSettings=') and current_section:
                    # Extract the part inside parentheses
                    match = re.match(r'OptionSettings=\((.*)\)', line)
                    if match:
                        option_str = match.group(1)
                        # Split by commas not inside quotes or parentheses
                        pairs = re.split(r',(?![^\(]*\))', option_str)
                        for pair in pairs:
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"')
                                settings[current_section][key] = value
                    continue
                # Fallback: parse key=value pairs
                if '=' in line and current_section:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    settings[current_section][key] = value
            return settings
        except Exception as e:
            print(f"Custom parser error: {e}")
            raise
    
    def _load_palworld_config_ini(self, config_path: str) -> Dict[str, Dict[str, str]]:
        """Fallback to standard configparser"""
        config = configparser.ConfigParser(strict=False)
        config.optionxform = lambda optionstr: optionstr  # preserve case
        config.read(config_path)
        return {section: dict(config.items(section)) for section in config.sections()}
        
    def save_palworld_config(self, config_path: str, settings: Dict[str, Dict[str, str]]):
        """Update only the values in OptionSettings=(...) that have changed, preserving all original formatting, quoting, and order."""
        # Read the original file
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the OptionSettings line
        option_settings_pattern = re.compile(r"(OptionSettings=\()(.*?)(\))", re.DOTALL)
        match = option_settings_pattern.search(content)
        if not match:
            raise ValueError("OptionSettings line not found in config file.")

        option_str = match.group(2)
        original_option_str = option_str  # Keep for in-place replacement
        new_options = settings.get("PalWorldSettings", {})

        # Robust parser for key=value pairs, handling nested parentheses and quoted strings
        pairs = []
        buf = ''
        in_quotes = False
        paren_level = 0
        i = 0
        while i < len(option_str):
            c = option_str[i]
            if c == '"':
                buf += c
                in_quotes = not in_quotes
                i += 1
            elif c == '(' and not in_quotes:
                paren_level += 1
                buf += c
                i += 1
            elif c == ')' and not in_quotes:
                paren_level -= 1
                buf += c
                i += 1
            elif c == ',' and not in_quotes and paren_level == 0:
                if buf:
                    pairs.append(buf)
                buf = ''
                i += 1
            else:
                buf += c
                i += 1
        if buf:
            pairs.append(buf)

        # For each key, if value changed, replace only the value in the original string
        option_str_new = option_str
        for pair in pairs:
            if '=' not in pair:
                continue
            key, value = pair.split('=', 1)
            key = key.strip()
            orig_value = value
            if key in new_options:
                # Remove quotes for comparison
                orig_val_clean = orig_value.strip('"')
                new_val = new_options[key]
                if new_val is None:
                    new_val = ''
                # Only update if different
                if orig_val_clean != new_val:
                    # Preserve original quoting if present, else quote if empty
                    if orig_value.startswith('"') and orig_value.endswith('"'):
                        value_str = f'"{new_val}"'
                    elif new_val == '':
                        value_str = '""'
                    else:
                        value_str = new_val
                    # Use a lambda to avoid group reference issues
                    pattern = re.compile(rf'({re.escape(key)}\s*=\s*){re.escape(orig_value)}')
                    option_str_new = pattern.sub(lambda m: m.group(1) + value_str, option_str_new, count=1)

        # Replace only the OptionSettings string in the file
        new_content = option_settings_pattern.sub(lambda m: f"{m.group(1)}{option_str_new}{m.group(3)}", content, count=1)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    def get_config_fields(self) -> Dict[str, Dict[str, Any]]:
        """Get the configuration fields structure based on official PalWorld documentation"""
        return {
            "PalWorldSettings": {
                # Server Settings
                "ServerName": str,
                "ServerDescription": str,
                "AdminPassword": str,
                "ServerPassword": str,
                "ServerPlayerMaxNum": int,
                "PublicIP": str,
                "PublicPort": int,
                
                # Game Balance Settings
                "Difficulty": ["None", "Easy", "Normal", "Hard"],
                "DayTimeSpeedRate": float,
                "NightTimeSpeedRate": float,
                "ExpRate": float,
                "DeathPenalty": ["None", "Item", "ItemAndEquipment", "All"],
                "GuildPlayerMaxNum": int,
                
                # Pal Settings
                "PalCaptureRate": float,
                "PalSpawnNumRate": float,
                "PalDamageRateAttack": float,
                "PalDamageRateDefense": float,
                "PalStaminaDecreaceRate": float,
                "PalStomachDecreaceRate": float,
                "PalAutoHPRegeneRate": float,
                "PalAutoHpRegeneRateInSleep": float,
                "PalEggDefaultHatchingTime": float,
                
                # Player Settings
                "PlayerDamageRateAttack": float,
                "PlayerDamageRateDefense": float,
                "PlayerStaminaDecreaceRate": float,
                "PlayerStomachDecreaceRate": float,
                "PlayerAutoHPRegeneRate": float,
                "PlayerAutoHpRegeneRateInSleep": float,
                
                # Base Camp Settings
                "BaseCampMaxNumInGuild": int,
                "BaseCampWorkerMaxNum": int,
                
                # Building Settings
                "BuildObjectDamageRate": float,
                "BuildObjectDeteriorationDamageRate": float,
                "MaxBuildingLimitNum": int,
                
                # Collection Settings
                "CollectionDropRate": float,
                "CollectionObjectHpRate": float,
                "CollectionObjectRespawnSpeedRate": float,
                
                # Enemy Settings
                "EnemyDropItemRate": float,
                
                # Item Settings
                "ItemWeightRate": float,
                "EquipmentDurabilityDamageRate": float,
                
                # Gameplay Settings
                "bEnableFastTravel": bool,
                "bEnableInvaderEnemy": bool,
                "bHardcore": bool,
                "bPalLost": bool,
                "bShowPlayerList": bool,
                "bCharacterRecreateInHardcore": bool,
                "bInvisibleOtherGuildBaseCampAreaFX": bool,
                "bIsRandomizerPalLevelRandom": bool,
                "bIsUseBackupSaveData": bool,
                "bBuildAreaLimit": bool,
                "bAllowGlobalPalboxExport": bool,
                "bAllowGlobalPalboxImport": bool,
                
                # Randomizer Settings
                "RandomizerSeed": int,
                "RandomizerType": ["None", "Region", "All"],
                
                # Crossplay Settings
                "CrossplayPlatforms": str,
                "AllowConnectPlatform": str,
                
                # Chat Settings
                "ChatPostLimitPerMinute": int,
                
                # Supply Drop Settings
                "SupplyDropSpan": int,
                
                # Sync Settings
                "ServerReplicatePawnCullDistance": int,
                "ItemContainerForceMarkDirtyInterval": int,
                
                # API Settings
                "RESTAPIEnabled": bool,
                "RESTAPIPort": int,
                "RCONEnabled": bool,
                "RCONPort": int,
                
                # Log Settings
                "LogFormatType": ["Text", "Json"]
            }
        }
        
    def validate_config(self, settings: Dict[str, Dict[str, str]]) -> bool:
        """Validate configuration settings"""
        config_fields = self.get_config_fields()
        
        for section, fields in config_fields.items():
            if section not in settings:
                continue
                
            for field_name, field_type in fields.items():
                if field_name not in settings[section]:
                    continue
                    
                value = settings[section][field_name]
                
                # Validate based on field type
                if field_type == bool:
                    if value.lower() not in ['true', 'false']:
                        return False
                elif field_type == int:
                    try:
                        int(value)
                    except ValueError:
                        return False
                elif field_type == float:
                    try:
                        float(value)
                    except ValueError:
                        return False
                elif isinstance(field_type, list):
                    if value not in field_type:
                        return False
                        
        return True
        
    def get_default_config(self) -> Dict[str, Dict[str, str]]:
        """Get default PalWorld configuration based on official documentation"""
        return {
            "PalWorldSettings": {
                # Server Settings
                "ServerName": "PalWorld Server",
                "ServerDescription": "A PalWorld server",
                "AdminPassword": "",
                "ServerPassword": "",
                "ServerPlayerMaxNum": "32",
                "PublicIP": "",
                "PublicPort": "8211",
                
                # Game Balance Settings
                "Difficulty": "Normal",
                "DayTimeSpeedRate": "1.000000",
                "NightTimeSpeedRate": "1.000000",
                "ExpRate": "1.000000",
                "DeathPenalty": "All",
                "GuildPlayerMaxNum": "20",
                
                # Pal Settings
                "PalCaptureRate": "1.000000",
                "PalSpawnNumRate": "1.000000",
                "PalDamageRateAttack": "1.000000",
                "PalDamageRateDefense": "1.000000",
                "PalStaminaDecreaceRate": "1.000000",
                "PalStomachDecreaceRate": "1.000000",
                "PalAutoHPRegeneRate": "1.000000",
                "PalAutoHpRegeneRateInSleep": "1.000000",
                "PalEggDefaultHatchingTime": "72.000000",
                
                # Player Settings
                "PlayerDamageRateAttack": "1.000000",
                "PlayerDamageRateDefense": "1.000000",
                "PlayerStaminaDecreaceRate": "1.000000",
                "PlayerStomachDecreaceRate": "1.000000",
                "PlayerAutoHPRegeneRate": "1.000000",
                "PlayerAutoHpRegeneRateInSleep": "1.000000",
                
                # Base Camp Settings
                "BaseCampMaxNumInGuild": "4",
                "BaseCampWorkerMaxNum": "15",
                
                # Building Settings
                "BuildObjectDamageRate": "1.000000",
                "BuildObjectDeteriorationDamageRate": "1.000000",
                "MaxBuildingLimitNum": "0",
                
                # Collection Settings
                "CollectionDropRate": "1.000000",
                "CollectionObjectHpRate": "1.000000",
                "CollectionObjectRespawnSpeedRate": "1.000000",
                
                # Enemy Settings
                "EnemyDropItemRate": "1.000000",
                
                # Item Settings
                "ItemWeightRate": "1.000000",
                "EquipmentDurabilityDamageRate": "1.000000",
                
                # Gameplay Settings
                "bEnableFastTravel": "True",
                "bEnableInvaderEnemy": "True",
                "bHardcore": "False",
                "bPalLost": "False",
                "bShowPlayerList": "True",
                "bCharacterRecreateInHardcore": "False",
                "bInvisibleOtherGuildBaseCampAreaFX": "False",
                "bIsRandomizerPalLevelRandom": "False",
                "bIsUseBackupSaveData": "True",
                "bBuildAreaLimit": "False",
                "bAllowGlobalPalboxExport": "False",
                "bAllowGlobalPalboxImport": "False",
                
                # Randomizer Settings
                "RandomizerSeed": "0",
                "RandomizerType": "None",
                
                # Crossplay Settings
                "CrossplayPlatforms": "(Steam,Xbox,PS5,Mac)",
                "AllowConnectPlatform": "",
                
                # Chat Settings
                "ChatPostLimitPerMinute": "0",
                
                # Supply Drop Settings
                "SupplyDropSpan": "0",
                
                # Sync Settings
                "ServerReplicatePawnCullDistance": "10000",
                "ItemContainerForceMarkDirtyInterval": "5",
                
                # API Settings
                "RESTAPIEnabled": "True",
                "RESTAPIPort": "8212",
                "RCONEnabled": "False",
                "RCONPort": "25575",
                
                # Log Settings
                "LogFormatType": "Text"
            }
        } 