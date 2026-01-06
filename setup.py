import os
import sys
import subprocess
import platform

def install_packages():
    """Installiere alle benötigten Python-Pakete"""
    print("🚀 Installation des ultimativen Crypto-Signal-Bots...")
    
    # Überprüfe Python-Version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 oder höher wird benötigt")
        return False
    
    print(f"✅ Python {sys.version} gefunden")
    
    # Installiere pip, falls nicht vorhanden
    try:
        import pip
    except ImportError:
        print("🔧 Installiere pip...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
    
    # Installiere die benötigten Pakete
    requirements = [
        "requests",
        "pandas", 
        "numpy",
        "matplotlib",
        "python-telegram-bot",
        "pandas_ta",
        "plotly",
        "python-dotenv"
    ]
    
    print("📦 Installiere Python-Abhängigkeiten...")
    
    for package in requirements:
        try:
            print(f"   Installiere {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            print(f"❌ Fehler bei der Installation von {package}")
            return False
    
    print("✅ Alle Abhängigkeiten erfolgreich installiert!")
    
    # Hinweise zur Konfiguration
    print("\n📝 Konfiguration:")
    print("1. Bearbeite die Datei .env mit deinem Bot-Token und Chat-ID")
    print("2. Starte den Bot mit: python run_bot.py")
    
    return True

if __name__ == "__main__":
    install_packages()