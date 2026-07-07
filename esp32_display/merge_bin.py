Import("env")
import os

def make_merged_bin(source, target, env):
    build_dir = env.subst("$BUILD_DIR")
    mcu = env.get("BOARD_MCU", "esp32c3")
    
    # Chemins vers les 3 fichiers générés par PlatformIO
    bootloader = os.path.join(build_dir, "bootloader.bin")
    partitions = os.path.join(build_dir, "partitions.bin")
    firmware = os.path.join(build_dir, "firmware.bin")
    
    # Emplacement et nom de ton fichier unique final
    output = os.path.join(env.subst("$PROJECT_DIR"), "FIRMWARE_UNIQUE.bin")
    
    # Commande de l'outil officiel Espressif pour fusionner les fichiers
    cmd = f'"{env.subst("$PYTHONEXE")}" -m esptool --chip {mcu} merge_bin -o "{output}" --flash_mode dio --flash_size 4MB 0x0000 "{bootloader}" 0x8000 "{partitions}" 0x10000 "{firmware}"'
    
    print("\n=======================================================")
    print("🪄 FUSION DES FICHIERS BINAIRES EN UN SEUL FICHIER...")
    env.Execute(cmd)
    print(f"✅ TERMINÉ ! Le fichier est prêt : {output}")
    print("=======================================================\n")

# Dit à PlatformIO de lancer ce script tout à la fin de la compilation
env.AddPostAction("$BUILD_DIR/firmware.bin", make_merged_bin)