#!/usr/bin/env python3
"""
Skript zur Validierung der Installation des Crypto-Signal-Bots
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Überprüft, ob eine Datei existiert"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - FEHLT")
        return False

def check_module_installed(module_name, package_name=None):
    """Überprüft, ob ein Python-Modul installiert ist"""
    try:
        if module_name == "telegram":
            importlib.import_module("telegram")
        else:
            importlib.import_module(module_name)
        print(f"✅ Modul installiert: {module_name}")
        return True
    except ImportError:
        pkg_name = package_name or module_name
        print(f"❌ Modul fehlt: {module_name} (installiere mit: pip install {pkg_name})")
        return False

def validate_setup():
    """Führt die vollständige Validierung durch"""
    print("🔍 Validiere die Installation des ultimativen Crypto-Signal-Bots...")
    print("")
    
    # Überprüfe Dateien
    files_ok = True
    files_ok &= check_file_exists("main.py", "Hauptcode")
    files_ok &= check_file_exists("config.py", "Konfigurationsdatei")
    files_ok &= check_file_exists("requirements.txt", "Abhängigkeiten")
    files_ok &= check_file_exists(".env", "Umgebungsvariablen")
    files_ok &= check_file_exists("run_bot.py", "Startskript")
    files_ok &= check_file_exists("setup.py", "Installationsskript")
    files_ok &= check_file_exists("README.md", "Dokumentation")
    
    print("")
    
    # Überprüfe Python-Module
    modules_ok = True
    modules_ok &= check_module_installed("requests")
    modules_ok &= check_module_installed("pandas")
    modules_ok &= check_module_installed("numpy")
    modules_ok &= check_module_installed("matplotlib")
    modules_ok &= check_module_installed("telegram", "python-telegram-bot")
    modules_ok &= check_module_installed("pandas_ta")
    modules_ok &= check_module_installed("plotly")
    modules_ok &= check_module_installed("dotenv", "python-dotenv")
    
    print("")
    
    # Überprüfe .env-Konfiguration
    env_ok = True
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            env_content = f.read()
            if "DEIN_BOT_TOKEN" in env_content or "8588495016:AAHEmP_g5guaLi_PwxLVbFjMKkuB3JD09HQ" in env_content:
                print("⚠️  .env-Datei gefunden, aber Token ist noch nicht konfiguriert")
                env_ok = False
            elif "DEINE_CHAT_ID" in env_content or "999286801" in env_content:
                print("⚠️  .env-Datei gefunden, aber Chat-ID ist noch nicht konfiguriert")
                env_ok = False
            else:
                print("✅ .env-Datei korrekt konfiguriert")
    else:
        print("❌ .env-Datei fehlt")
        env_ok = False
    
    print("")
    
    # Gesamtergebnis
    if files_ok and modules_ok and env_ok:
        print("🎉 Alles bereit! Der Crypto-Signal-Bot ist erfolgreich eingerichtet.")
        print("💡 Starte den Bot mit: python run_bot.py")
        return True
    else:
        print("❌ Einige Komponenten fehlen oder sind nicht korrekt konfiguriert.")
        print("   Stelle sicher, dass alle Dateien vorhanden sind und alle Module installiert wurden.")
        print("   Konfiguriere die .env-Datei mit deinem Bot-Token und Chat-ID.")
        return False

if __name__ == "__main__":
    success = validate_setup()
    sys.exit(0 if success else 1)